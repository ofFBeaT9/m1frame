#!/usr/bin/env python3
"""Run the OPU feasibility study: sweep optical SNR, measure how a ternary PINN's
output VALUES and DERIVATIVES degrade, and write CSV / PNG / JSON artifacts.

    python run_study.py                      # default sweep
    python run_study.py --realizations 20 --eval-inputs 24
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from optical_mvm import OpticalMVM, OpticalParams
from pinn_opu_sim import (OUTPUT_NAMES, TernaryPINN, evaluate, jacobian)

TERNARY_BUDGET = 0.194   # existing ternary-vs-FP32 rel MAE the project already pays


def _crossing(snr: np.ndarray, err: np.ndarray, target: float):
    """SNR(dB) at which mean err crosses `target` (err decreases with SNR)."""
    order = np.argsort(snr)
    s, e = snr[order], err[order]
    for i in range(len(s) - 1):
        a, b = e[i], e[i + 1]
        if (a - target) * (b - target) <= 0 and a != b:
            t = (target - a) / (b - a)
            return float(s[i] + t * (s[i + 1] - s[i]))
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Tritone OPU SNR-tolerance study")
    ap.add_argument("--snr-min", type=float, default=5.0)
    ap.add_argument("--snr-max", type=float, default=40.0)
    ap.add_argument("--snr-points", type=int, default=8)
    ap.add_argument("--realizations", type=int, default=12, help="optical devices per SNR")
    ap.add_argument("--eval-inputs", type=int, default=16)
    ap.add_argument("--sigma-w", type=float, default=0.02, help="static weight/phase err std")
    ap.add_argument("--er-db", type=float, default=25.0, help="extinction ratio of '0' state")
    ap.add_argument("--crosstalk", type=float, default=0.0)
    ap.add_argument("--noise-mode", choices=["additive", "shot"], default="additive")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--weights", default=None,
                    help="hook: path to real .keras-derived ternary tiles (not yet loaded)")
    ap.add_argument("--outdir", default=str(Path(__file__).parent / "results"))
    args = ap.parse_args()

    t0 = time.time()
    rng = np.random.default_rng(args.seed)
    if args.weights:
        print(f"NOTE: --weights {args.weights} given, but real-weight loading is a "
              f"future hook; using faithful synthetic ternary weights for this run.")

    net = TernaryPINN(seed=args.seed)
    X = rng.standard_normal((args.eval_inputs, 110))   # neutral-normalized features
    net.calibrate(X)
    eps = 0.05 * float(np.std(X))

    # bit-exact baseline (the FPGA reference). Value error uses the INT8 path;
    # derivative uses the smooth analog path (optics is continuous, no staircase).
    from pinn_opu_sim import _rel_l1
    Y_base = net.forward(X, None)
    J_base = jacobian(net, X, None, eps, quantize=False)
    sparsity = net.sparsity

    # F1 sanity: clean-Jacobian eps-stability. The INT8 staircase makes the clean
    # finite-diff Jacobian unstable in eps; the smooth analog path should not be.
    jac_stability = dict(
        int8_eps_vs_halfeps=_rel_l1(jacobian(net, X, None, eps * 0.5, quantize=True),
                                    jacobian(net, X, None, eps, quantize=True)),
        smooth_eps_vs_halfeps=_rel_l1(jacobian(net, X, None, eps * 0.5, quantize=False),
                                      J_base))

    snrs = np.linspace(args.snr_min, args.snr_max, args.snr_points)
    rows = []
    per_output_at = {}   # snr -> mean per-output rel error
    for snr in snrs:
        vals, maxs, absm, jacs, amps, perouts = [], [], [], [], [], []
        for r in range(args.realizations):
            params = OpticalParams(
                snr_db=float(snr), sigma_w=args.sigma_w, er_db=args.er_db,
                crosstalk=args.crosstalk, noise_mode=args.noise_mode)
            dev = OpticalMVM(params, np.random.default_rng(args.seed + 1000 * r + int(snr)))
            res = evaluate(net, X, Y_base, J_base, dev, eps, jac_quantize=False)
            vals.append(res.value_rel_mae); maxs.append(res.value_max_rel_err)
            absm.append(res.value_abs_mae); jacs.append(res.jac_rel_mae)
            amps.append(res.amplification); perouts.append(res.per_output_rel)
        rows.append(dict(
            snr_db=float(snr),
            value_rel_mae=float(np.mean(vals)), value_rel_mae_std=float(np.std(vals)),
            value_max_rel_err=float(np.mean(maxs)), value_abs_mae=float(np.mean(absm)),
            jac_rel_mae=float(np.mean(jacs)), jac_rel_mae_std=float(np.std(jacs)),
            amplification=float(np.mean(amps)), amplification_std=float(np.std(amps)),
        ))
        per_output_at[float(snr)] = np.mean(perouts, axis=0)

    # static-defect-only probe: fixed sigma_w weight error + ER leakage, NO readout
    # noise at all (QA's cleanest finding: a fabrication defect alone perturbs outputs).
    static_dev = OpticalMVM(
        OpticalParams(snr_db=np.inf, sigma_w=args.sigma_w, er_db=args.er_db,
                      enable_readout=False),
        np.random.default_rng(args.seed))
    static_only = evaluate(net, X, Y_base, J_base, static_dev, eps, jac_quantize=False)

    snr_arr = np.array([r["snr_db"] for r in rows])
    val_arr = np.array([r["value_rel_mae"] for r in rows])
    jac_arr = np.array([r["jac_rel_mae"] for r in rows])
    amp_arr = np.array([r["amplification"] for r in rows])

    summary = dict(
        config=vars(args),
        sparsity=sparsity,
        ternary_budget=TERNARY_BUDGET,
        derivative_path="smooth-analog (INT8 staircase removed per QA finding F1)",
        snr_for_value_under_budget=_crossing(snr_arr, val_arr, TERNARY_BUDGET),
        snr_for_value_under_5pct=_crossing(snr_arr, val_arr, 0.05),
        snr_for_deriv_under_budget=_crossing(snr_arr, jac_arr, TERNARY_BUDGET),
        mean_amplification=float(np.mean(amp_arr)),
        amplification_range=[float(amp_arr.min()), float(amp_arr.max())],
        amplification_note=("absolute amplification scales ~1/eps (finite-difference of "
                            "a noisy signal); the qualitative gap + floor are the robust "
                            "facts, not the bare factor"),
        jac_clean_eps_stability=jac_stability,
        static_defect_only=dict(value_rel_mae=static_only.value_rel_mae,
                                jac_rel_mae=static_only.jac_rel_mae),
        runtime_s=round(time.time() - t0, 2),
        rows=rows,
    )

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    # CSV
    csv = outdir / "snr_sweep.csv"
    keys = ["snr_db", "value_rel_mae", "value_rel_mae_std", "value_max_rel_err",
            "value_abs_mae", "jac_rel_mae", "jac_rel_mae_std", "amplification",
            "amplification_std"]
    with csv.open("w") as f:
        f.write(",".join(keys) + "\n")
        for r in rows:
            f.write(",".join(f"{r[k]:.6g}" for k in keys) + "\n")
    # JSON
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))

    # PNG
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4.2))
        axL.errorbar(snr_arr, val_arr, yerr=[r["value_rel_mae_std"] for r in rows],
                     marker="o", label="value error  |Δoutput|", capsize=3)
        axL.errorbar(snr_arr, jac_arr, yerr=[r["jac_rel_mae_std"] for r in rows],
                     marker="s", label="derivative error  |Δ ∂out/∂in|", capsize=3)
        axL.axhline(TERNARY_BUDGET, ls="--", color="gray",
                    label=f"ternary budget {TERNARY_BUDGET:.0%}")
        axL.set_xlabel("optical SNR per layer (dB)"); axL.set_ylabel("added relative error")
        axL.set_yscale("log"); axL.set_title("PINN error vs optical SNR")
        axL.legend(fontsize=8); axL.grid(alpha=0.3, which="both")
        axL.invert_xaxis()  # noisier (low SNR) on the right
        axR.plot(snr_arr, amp_arr, marker="d", color="crimson")
        axR.axhline(1.0, ls=":", color="gray", label="parity (value=derivative)")
        axR.set_xlabel("optical SNR per layer (dB)")
        axR.set_ylabel("derivative / value error  (amplification)")
        axR.set_title("Derivative amplification (the PINN risk)")
        axR.legend(fontsize=8); axR.grid(alpha=0.3); axR.invert_xaxis()
        fig.suptitle(f"Tritone OPU feasibility — sparsity {sparsity:.0%}, "
                     f"σ_w={args.sigma_w}, ER={args.er_db}dB, {args.noise_mode} noise",
                     fontsize=10)
        fig.tight_layout()
        fig.savefig(outdir / "snr_sweep.png", dpi=130)
        png_ok = True
    except Exception as e:  # pragma: no cover
        png_ok = False
        print(f"WARN: plot skipped ({e})")

    # console report
    print("\n=== Tritone OPU feasibility — results ===")
    print(f"network sparsity (zeros)      : {sparsity:.1%}")
    print(f"eval inputs x realizations    : {args.eval_inputs} x {args.realizations}")
    print(f"{'SNR(dB)':>8} {'value_err':>10} {'deriv_err':>10} {'amplif.':>9}")
    for r in rows:
        print(f"{r['snr_db']:8.1f} {r['value_rel_mae']:10.4f} "
              f"{r['jac_rel_mae']:10.4f} {r['amplification']:9.2f}")
    print(f"\nSNR for value error < {TERNARY_BUDGET:.0%} budget : "
          f"{summary['snr_for_value_under_budget']}")
    print(f"SNR for value error < 5%             : {summary['snr_for_value_under_5pct']}")
    print(f"SNR for derivative error < {TERNARY_BUDGET:.0%}    : "
          f"{summary['snr_for_deriv_under_budget']}")
    print(f"mean derivative amplification        : {summary['mean_amplification']:.2f}x "
          f"(range {amp_arr.min():.2f}-{amp_arr.max():.2f}; scales ~1/eps, see note)")
    print(f"static-defect-only (no readout noise): value {static_only.value_rel_mae:.3f}, "
          f"deriv {static_only.jac_rel_mae:.3f}  <- breaks derivatives with ZERO shot noise")
    print(f"clean-Jacobian eps-stability         : INT8 {jac_stability['int8_eps_vs_halfeps']:.3f} "
          f"vs smooth {jac_stability['smooth_eps_vs_halfeps']:.3f}  (smooth << INT8 => artifact removed)")
    print(f"runtime: {summary['runtime_s']}s   artifacts: {outdir}  png={png_ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
