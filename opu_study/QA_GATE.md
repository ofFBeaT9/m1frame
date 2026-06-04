# QA Gate — Tritone OPU Feasibility Study

QA agent reviews (a) the roadmap before Dev, then (b) the executed results.
Gate values: **PASS** (proceed) · **CONCERNS** (proceed only after listed fixes) · **FAIL** (rework).

---

## Gate 1 — Roadmap review (pre-Dev)

**Reviewer:** QA persona, independent critical pass over `ROADMAP.md`.
**Verdict: CONCERNS** — roadmap is sound, but 5 correctness issues MUST be fixed in implementation
before the numbers can be trusted. All are folded into the Dev stories below.

| ID | Severity | Finding | Required fix |
|---|---|---|---|
| **F1** | 🔴 High | **Finite-difference Jacobian vs INT8 quantization.** Perturbing a float input by a tiny ε may not move the INT8-quantized activation at all → derivative metric measures the quantization staircase, not optics. A naive implementation reports garbage. | Compare `J_optical` vs `J_baseline` with the **same** ε through the **same** INT8 path so quantization is **common-mode** and cancels in the *relative* metric. Use ε ≈ 0.05·std(input) (crosses ≥1 level) and average over many inputs × realizations. |
| **F2** | 🟠 Med | **Shot noise is signal-dependent** (∝√signal), but roadmap's primary term is fixed-σ Gaussian. Fixed-σ is fine for a clean SNR axis but is not the only physically real regime. | Implement BOTH: `additive` (default, clean SNR sweep) and `shot` (var ∝ \|psum\|). Report the sweep under additive; spot-check shot. |
| **F3** | 🟠 Med | **Division by zero / blow-ups.** `σ_add = rms(psum)·…` is 0 for an all-zero layer/sample; `rel_mae` denominator explodes for sigmoid outputs near 0. | Floor `rms` with a small ε; use `(\|y_base\| + 1e-3)` denominators **and** also report absolute MAE as a cross-check. |
| **F4** | 🟡 Low | **"19.4 % budget" semantics.** The 19.4 % is the *real* model's ternary-vs-FP32 error. The synthetic baseline here is already ternary, so the measured error is **additional** optical error on top. | Frame the metric explicitly as *added* error; plot the 19.4 % line as a reference and report SNR at multiple thresholds (5 %, 19.4 %), not just one. |
| **F5** | 🟡 Low | **Per-layer vs end-to-end SNR.** σ scaled by each layer's own rms ⇒ the SNR knob is *per-layer*; end-to-end is worse after 7 layers. Could be misread. | Document that the swept SNR is per-layer; report the observed end-to-end degradation separately. |

**Strengths noted:** baseline is correctly pinned to the real `tpu_driver.py` MAC contract; effects are
individually switchable (testable limits); scope is honestly bounded; the real-weights hook keeps the
study self-contained yet upgradeable. The central hypothesis (derivatives degrade faster) is the right
thing to measure and is directly decision-relevant.

**Condition to clear the gate:** F1–F5 implemented and covered by unit tests (Story S2/S4). Proceed to Dev.

---

## Gate 2 — Results review (post-Dev)

**Reviewers:** (1) independent QA sub-agent (read the code, re-ran everything, probed ε-sensitivity);
(2) QA persona final sign-off after the fix. **Verdict: PASS (with stated caveats).**

### What the independent audit confirmed (all re-run, not just read)
- `mac_baseline` is pure int64; full PINN baseline == independent integer recompute, **max diff 0.0**.
- Perfect optics reproduces the baseline Jacobian to **exactly 0.0** → the common-mode-quantization claim (F1) holds.
- Static device errors cached per layer; readout noise fresh per call → a device is internally consistent
  across the ±ε Jacobian evals (required for F1). 11/11 unit tests pass.
- Metric edge cases safe (`_rel_l1(0,0)=0`, amp guard, `_crossing` returns None when never met).

### The one real finding — and the fix applied
| ID | Sev | Finding | Resolution |
|---|---|---|---|
| **F6** | 🔴→✅ | The **72× amplification was inflated by the INT8 quantization staircase**: finite-differencing a step function is ill-conditioned even with zero optical noise (clean INT8 Jacobian shifts **189 %** when ε halves). The bare "72×" overclaims. | **Fixed, not just caveated.** Derivative metric now runs on the **smooth analog path** (optics is continuous — INT8 is an FPGA-only trick). Verified: clean-Jacobian ε-stability **INT8 1.889 → smooth 0.033**. The staircase artifact is removed; residual ε-dependence of the *noise-driven* factor is the genuine 1/ε behaviour of differencing noisy data and is reported as **directional only**. |

### Robust, ε-independent facts the verdict rests on
- **Value error** (bit-exact baseline): crosses the 19 % ternary budget at **SNR ≈ 18.2 dB/layer**; static-defect floor **≈ 7.8 %**.
- **Static-defect-only** (fixed 2 % weight error, *zero* readout noise — cannot be a finite-diff artifact):
  **value 8.1 % vs derivative 51.9 %** → derivatives ~**6×** more fragile, ε-stable.
- Derivative error **never** reaches the 19 % budget at any SNR or ε (floor ≥ 1.68 across the audit's ε sweep).

**Gate cleared.** Headline must report the qualitative value/derivative gap + the ε-stable static-defect
result, **not** the bare amplification factor. Caveats carried into `FINAL_REPORT.md`: synthetic weights
(real-weight hook is next), derivative is a proxy for the full FHN residual.
