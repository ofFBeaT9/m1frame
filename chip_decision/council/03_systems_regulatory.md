# Council 3 — Systems / Workload / Deployment Architect

*Position paper. Verdict: manufacture a small digital ternary ASIC; determinism is the regulatory anchor.*

## What the workload demands
The PINN is tiny: 7 layers, ≤512 wide, 110→5, ~500k MACs/inference (multiplier-free → adds only). Inference
rate needs are modest and intermittent (a diagnostic pass or a drug-trial parameter sweep, not kHz streaming).
**Field retraining: never** — train once in the cloud, validate, freeze, lock for regulatory submission. What
ships is a frozen weight artifact (the OPU study confirms training can't survive analog noise anyway).

## Edge is the target
IBS diagnosis at point of care, bedside virtual drug trials, patient-specific prediction → low latency,
data locality (HIPAA), milliwatt power, medical-device price points. At 105 mW on a $20 board Tritone
already proves the edge case; the question is whether an ASIC buys enough over a hardened FPGA/DSP.

## Regulatory determinism is non-negotiable
FDA AI/ML SaMD (Jan 2025 draft, Aug 2025 PCCP final) requires: a **locked algorithm** at submission;
**reproducible, auditable** inference (same input → same output, every device/run); SBOM traceability to
specific weights + code; predetermined change-control for any weight update. Analog non-determinism
(thermal noise, aging, fab variation; the optical path's ~7.8 % irreducible noise) fails this immediately —
you cannot file a 510(k) that says "outputs are approximately correct." **Bit-exact digital ternary
arithmetic is the regulatory prerequisite, not a nicety.**

## Recommended system architecture
| Layer | Component | Role |
|---|---|---|
| Training | Cloud GPU cluster | one-time PINN train + validate + freeze |
| Cert artifact | frozen weights + test vectors | regulatory submission, golden reference |
| Edge inference | custom low-power digital ternary ASIC (28 nm) | deterministic, <10 mW, ~$5–8/unit @ volume |
| Host | ARM Cortex-M33 | I/O, UI, BLE, audit logging |
| Dev/fallback | Tang Nano 9K FPGA | prototyping, lab weight validation |

**VERDICT:** manufacture a small digital ternary ASIC. The value isn't throughput — it's deterministic,
sub-10 mW, **certifiable** inference at medical-device cost. Analog/optical is disqualified by both gradient
physics and FDA reproducibility.

*Sources:* FDA AI/ML SaMD guidance (fda.gov); FDA AI/ML SaMD Action Plan; SaMD compliance guides (2025/2026).
