# Council 2 — Analog / Photonic / In-Memory Compute Architect

*Position paper. Verdict: analog photonics fails; only an in-memory ternary macro is worth considering.*
*(NOTE: the red-team later corrected this paper's "fully deterministic" claim for charge-domain CIM — see `04_redteam_qa_gate.md` F1.)*

## Technology comparison for ternary inference
| Tech | TOPS/W | Ternary fit | Noise/defect floor | Foundry today | Verdict |
|---|---|---|---|---|---|
| Si-photonic MZI mesh | ~0.28–160 (scale-dependent) | good (3 phase levels) | **7.8 % static — confirmed** | AIM Photonics, IMEC | structurally limited |
| Microring (MRR) weight bank | denser via WDM | 3 resonance states | thermal drift ±0.1 nm/°C | same, harder yield | worse stability |
| Analog ReRAM crossbar | ~10–100 (est.) | excellent (3 conductance levels, free sparsity) | cycle σ ~5–10 %, stuck cells | Weebit/onsemi, TSMC 130 nm | promising, immature (3–5 yr) |
| **Charge-domain SRAM CIM** | **~1000–2941 (28 nm, ternary)** | excellent (2-bit charge-share, no DAC) | *analog + ADC → see red-team F1* | TSMC 28/22 nm standard | best efficiency — **but not bit-exact** |

## Why photonics loses at this scale
Tritone's widest layer is 512. A 512×512 MZI mesh ≈ 262k thermo-optic phase shifters (~1 mW each) =
**~262 W tuning alone** (2500× the FPGA budget). ADC/DAC for 512 channels adds ~2.5–10 W. The photonic
energy argument only activates above N≈4096. At N=512 photonics is a liability.

## ReRAM
3-conductance ternary encoding is natural; 42 % zero-weights = zero-current rows (free sparsity). Weebit
AEC-Q100 (2025) shows progress, but stuck-cell yield at 512×512 = 262k cells and lack of a standard-cell
flow make a 2026 tapeout high-risk. ~3–5 year horizon.

## Recommended analog tech + role (pre-red-team)
Charge-domain ternary SRAM CIM in TSMC 28 nm as an inference co-processor to a small digital controller;
no photonic/ReRAM tapeout now; revisit ReRAM ~2028.

**VERDICT:** photonics fails on physics, ReRAM on maturity; an in-memory ternary macro is the only analog
path worth a tapeout — *as a co-processor, not a full-chip replacement.*

*Sources:* Intelligent Computing (microresonator PNNs); ACS Photonics (integrated PNN review); Frontiers in Physics (photonic DL accelerators); arXiv 2409.06604 (self-calibrated microring); ResearchGate (2941-TOPS/W charge-domain 10T SRAM CIM); PMC (disturbance-resilient ReRAM crossbars); arXiv 2505.11369 (microring neurons).
