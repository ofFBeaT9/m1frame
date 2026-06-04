# Tritone OPU Layer — Feasibility Roadmap (BMAD)

> **Method:** BMAD (Analyst → PM → Architect → Scrum Master → Dev → QA).
> **Shared memory:** miras (project: `default`). Each agent recalls before deciding and stores at handoff.
> **One-line goal:** Decide — with a cheap software experiment, not photonic hardware — whether an
> Optical Processing Unit (OPU) could replace Tritone's ternary MAC array without destroying the
> PINN accuracy that is the project's whole point.

---

## 0. Pipeline status

| Phase | Agent | Output | State |
|---|---|---|---|
| 1 | Analyst | Project Brief (§1) | ✅ |
| 2 | PM | PRD: goals, FR/NFR, success metrics (§2) | ✅ |
| 3 | Architect | Technical design: error model + harness (§3) | ✅ |
| 4 | Scrum Master | Epic + sharded stories (§4) | ✅ |
| 5 | **QA** | **Gate review of THIS roadmap** (`QA_GATE.md` §1) → CONCERNS, 5 fixes folded in | ✅ |
| 6 | Dev | Implementation + run (11/11 tests, sweep) | ✅ |
| 7 | QA | Independent audit + results gate (`QA_GATE.md` §2) → PASS w/ fix | ✅ |
| 8 | Analyst/PM | Verdict (`FINAL_REPORT.md`) + miras | ✅ |

---

## 1. Analyst — Project Brief

### Problem
Tritone today is a **multiplier-free ternary MAC array** (16×16 systolic PEs, weights ∈ {−1,0,+1},
INT8 activations, 0 DSP, ~105 mW) that runs a 7-layer PINN **bit-exact** (0.00000 max rel err) on a
$20 Tang Nano 9K. The user asked: *what if we add an Optical Processing Unit layer?*

Optical matrix-vector multiply (MVM) is fast and energy-cheap, but **analog** — it injects noise.
A PINN is unusually noise-sensitive because downstream value depends on **derivatives** of the network
output. So the question is not "is optics cool" (it is) but **"how much analog noise can this specific
PINN absorb before its 5 conductance outputs — and their sensitivities — go bad?"**

### Why ternary makes optics interesting (the upside hypothesis)
- **3 levels, not 256.** Optics struggles to hold high-precision analog weights; ternary needs only
  {−1 → 0-phase, +1 → π-phase, 0 → blocked}. Three well-separated states sidestep optics' #1 weakness.
- **Sparsity is free.** A `0` weight is *no light path*: zero energy, zero noise. Ternary is ~50–84% zeros.
- **The FPGA you already built is the natural OPU controller** (I/O, nonlinearity, INT8 scaling, ADC/DAC).

### The tension (the downside hypothesis — what we must measure)
Bit-exactness is Tritone's crown jewel and is the **opposite** of analog optics. PINNs amplify analog
noise through differentiation. **Core hypothesis to test:** *derivative error grows faster than value
error as optical SNR drops* — i.e. an OPU may pass a classifier's bar but fail a PINN's.

### Grounded anchors (from project memory / repo, not invented)
- Real ternary MAC semantics: `host/tpu_driver.py` (enc −1→00, 0→01, +1→10; INT16 partial sums).
- Architecture (7 Dense): 110→512 → [512→512→512]+skip → [512→128, 128→128, 512→128 proj]+skip → 128→5 sigmoid.
- Outputs: `g_Na, g_K, g_Ca, omega, coupling_strength` (sigmoid 0..1).
- Existing accuracy budget: ternarization already costs **19.4 % mean rel MAE** (τ=0.7). Optics must fit *under* that.
- Physics: FHN `dv/dt = v − v³/3 − w`, `dw/dt = ε(v + a − bw)` (a=0.7, b=0.6875, ε=0.078125).

---

## 2. PM — Product Requirements (PRD)

### Goal
Produce a **"PINN accuracy vs optical SNR" curve** plus a go/no-go verdict, in software, today.

### Functional requirements
- **FR1** — Bit-exact integer ternary MAC baseline that matches the hardware contract in `tpu_driver.py`.
- **FR2** — A physically-motivated optical-MVM error model with independently-toggleable effects:
  (a) additive readout noise (shot+thermal+ADC) parameterized by output **SNR(dB)**;
  (b) multiplicative weight/phase error on the ±1 states; (c) finite **extinction ratio** leakage on the
  `0` state; (d) optional inter-channel crosstalk.
- **FR3** — Faithful 7-layer ternary PINN forward pass (correct residual/skip topology, ReLU, sigmoid,
  per-layer INT8 activation scaling, τ=0.7 TWN ternarization, report actual sparsity).
- **FR4** — An SNR sweep harness that, per noise level, reports **value error** (rel MAE + max rel err on
  the 5 outputs) and **derivative error** (rel MAE of ∂outputs/∂inputs via finite difference), with
  mean±std over multiple noise realizations.
- **FR5** — Outputs: `results/snr_sweep.csv`, `results/snr_sweep.png`, `results/summary.json`.
- **FR6** — A `--weights` hook to drop in the real `.keras`-derived ternary tiles on the Pi later
  (default: faithful synthetic weights so the study runs self-contained here).

### Non-functional requirements
- **NFR1 — Correctness/determinism:** fully seeded; baseline must be *exactly* integer (asserted == reference).
- **NFR2 — Honesty:** clearly label what is real (MAC semantics, topology, sparsity, 5 outputs, 19.4 % budget)
  vs modeled (representative weights, derivative *proxy* for the full FHN residual).
- **NFR3 — Unit tested:** `tests/` covers the MAC baseline, each noise term's limiting behavior, and metrics.
- **NFR4 — Runs < ~30 s on CPU**, no GPU, numpy only.

### Success metrics (the decision)
1. **Usable-SNR threshold** = lowest SNR(dB) at which added value rel-MAE stays under the 19.4 % budget.
2. **Derivative amplification factor** = derivative-rel-MAE ÷ value-rel-MAE (hypothesis: > 1).
3. **Verdict:** GO (cheap follow-up worth it) / CONDITIONAL / NO-GO, with the numbers behind it.

### Out of scope (explicit)
Photonic layout/SPICE, training-through-optics / in-situ backprop, real `.keras` weights (hook only),
hardware procurement, energy/area modeling. This is a **feasibility gate**, not a design.

---

## 3. Architect — Technical Design

### Module layout (`opu_study/`)
```
optical_mvm.py     # ternary MAC baseline + OpticalMVM error model (the physics)
pinn_opu_sim.py    # 7-layer ternary PINN forward pass + metrics
run_study.py       # CLI: SNR sweep -> CSV + PNG + JSON
tests/test_optical_mvm.py   # correctness gate
results/           # generated artifacts
```

### Baseline MAC (must be bit-exact)
For weights `W ∈ {−1,0,+1}^{in×out}` and INT8 activations `a`: `psum = a @ W` in pure integer arithmetic.
This is the deterministic reference every optical run is compared against.

### Optical error model (per matmul; each term defaults physically plausible, each separately switchable)
1. **Additive readout noise** referred to the output:
   `σ_add = rms(psum_clean) · 10^(−SNR_dB/20)`, `psum ← psum + N(0, σ_add²)`. (Primary swept knob.)
2. **Weight/phase error** on nonzeros: `W_eff[w≠0] = W · (1 + N(0, σ_w))` (imperfect 0/π drive).
3. **Extinction-ratio leakage** on zeros: `W_eff[w=0] = 10^(−ER_dB/20) · N(0,1)` ("off" path leaks light).
4. **Crosstalk** (optional, default off): `psum_j ← psum_j + c·(psum_{j−1}+psum_{j+1})`.

### Forward pass (faithful topology)
`x(110) → Dense110→512+ReLU → [Dense512→512+ReLU → Dense512→512]+x → ReLU` (res_block_0)
`→ [Dense512→128+ReLU → Dense128→128]+[Dense512→128 proj] → ReLU` (res_block_2) `→ Dense128→5 → sigmoid`.
Every Dense matmul is routed through either the baseline (bit-exact) or the OpticalMVM path.
Per-layer INT8 activation scaling (`s = 127/max|a|`) mirrors the real harness.

### Metrics (per SNR level, averaged over R realizations × M inputs)
- `value_rel_mae   = mean |y_opt − y_base| / (|y_base| + ε)`
- `value_max_rel_err`
- `jac_rel_mae` over the Jacobian `∂y/∂x` (central finite difference on the 110 inputs) — the PINN-critical metric
- `amplification   = jac_rel_mae / value_rel_mae`

### Decision logic
Find `SNR*` where `value_rel_mae(SNR*) ≈ 0.194` (the existing ternary budget). Report `amplification`
across the sweep. GO if `SNR*` is comfortably reachable by real photonics (≳ literature 15–25 dB ONN range)
**and** amplification stays bounded; NO-GO if even high SNR can't keep derivatives sane.

---

## 4. Scrum Master — Epic & Stories

**Epic:** *Quantify the optical-noise tolerance of Tritone's ternary PINN to gate the OPU idea.*

| # | Story | Acceptance criteria |
|---|---|---|
| S1 | Ternary MAC baseline | `mac_baseline(a,W)` returns pure-integer `a@W`; unit test asserts exact equality vs numpy int reference on random ternary W. |
| S2 | OpticalMVM model | Each of the 4 effects implemented + individually switchable; tests confirm limits (SNR→∞ ⇒ noise→0; ER→∞ ⇒ no leak; σ_w=0 ⇒ weights unchanged). |
| S3 | PINN forward pass | 7-layer topology with correct skips; sparsity reported; baseline path == integer reference end-to-end. |
| S4 | Metrics + Jacobian | value & derivative metrics computed; finite-difference Jacobian verified against an analytic linear case. |
| S5 | Sweep + artifacts | `run_study.py` sweeps SNR, writes CSV/PNG/JSON with mean±std error bars. |
| S6 | QA gate (roadmap + results) | Independent review; gate = PASS/CONCERNS/FAIL recorded in `QA_GATE.md`; findings folded back in. |
| S7 | Verdict + miras | `FINAL_REPORT.md` states SNR*, amplification, GO/NO-GO; key facts stored to miras under `analyst/architect/qa`. |

### Risks
- **R1** — Synthetic weights may be optimistic/pessimistic vs real PINN → mitigate with the `--weights` hook + flag clearly.
- **R2** — Derivative *proxy* ≠ full FHN residual → label as proxy; note follow-up is to wire the real residual on the Pi.
- **R3** — Noise model could be miscalibrated → make every term switchable and unit-test limiting behavior (NFR3).

---
*Generated by the BMAD pipeline. QA gate review follows in `QA_GATE.md` before any Dev work proceeds.*
