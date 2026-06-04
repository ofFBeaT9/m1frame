# Council 4 — Red-Team / QA Gate

*Adversarial review of the draft synthesis. **GATE: PASS with concerns** (all folded into `../DECISION.md`).*

The core direction (digital ternary ASIC; reject photonics/ReRAM; cloud-train + edge-infer; FDA lock) is
sound. Five findings; F1 is a material contradiction in the council's own reasoning.

| ID | Sev | Finding | Fix |
|---|---|---|---|
| **F1** | 🔴 High | **Charge-domain SRAM CIM is NOT bit-exact.** It accumulates analog charge and reads via ADC (PVT variation, ADC offset/gain, bitline coupling). The ~2941 TOPS/W is an *analog* macro figure. Council-2's "fully deterministic" claim is wrong → it self-violates the FDA determinism rule used to reject optics. | Phase-2 = **fully-digital** ternary CIM (bit-serial/parallel, no ADC). Realistic **30–150 TOPS/W** (digital SRAM-CIM 34–75 TOPS/W @ 65 nm; CUTIE ~3.1 POps/W ternary @ 22 nm). 10–100× lower than the analog figure but deterministic & 510(k)-compatible. |
| **F2** | 🟠 Med | **Tape-out not justified yet.** Tiny workload runs on a Cortex-M33/FPGA; no unit volume, latency SLA, or power-critical scenario cited. | Gate NRE behind explicit triggers: (a) >500 units, (b) <5 mW envelope FPGA can't meet, or (c) submission needs certified silicon BOM. Until then FPGA + M33. SKY130 = optional learning tape-out. |
| **F3** | 🟠 Med | **SKY130 @ 130 nm is borderline at 200 MHz and not production-representative** (~5 mm² vs ~0.3 mm² @ 28 nm; different SRAM density/leakage/packaging). Lessons don't transfer cleanly. | Use SKY130 only as a functional-correctness + golden-vector vehicle. Don't extrapolate 40 mW / 8 GOPS. MPW delivery ~July 2026. |
| **F4** | 🟡 Low | **Weight-storage blind spot.** "Freeze+certify" doesn't say SRAM-loaded vs ROM. FDA lock needs an auditable boot chain. | Store weights in on-chip OTP or verified flash with **SHA-256** checked at boot; document in SBOM; any weight update → new 510(k) under PCCP. |
| **F5** | 🟡 Low | **"Analog wins at N≫4096" conflates analog-CIM with the general analog case.** | Rephrase: analog wins only if (a) non-regulated inference-only, (b) N≫4096, AND (c) stochastic output acceptable. Charge-domain CIM is *independently* disqualified by determinism. |

## Verified
- Charge-domain CIM uses ADC readout w/ PVT variation (ISLPED/TVLSI/MDPI 2022–2025) → "bit-exact" is not a property of the class.
- Digital ternary CIM realistic at 34–75 TOPS/W (65 nm); CUTIE ~3.1 POps/W ternary (22 nm). The 2941 figure is analog-only.
- SKY130 MPW ~$10–12k, ~July 2026 delivery (SkyWater/Cadence).
- FDA "locked algorithm" reproducibility is standard SaMD doctrine; functionally disqualifies non-deterministic analog inference.

*Sources:* ACM/IEEE ISLPED 2022 (P-8T charge-domain CIM); MDPI Electronics 2024 (hybrid-ADC CIM); arXiv 2411.06079 (SRAM-CIM review); IEEE TVLSI 2024 (quantized-ADC CIM); arXiv 2011.01713 (CUTIE); arXiv 2205.01569 (885.86 TOPS/W SRAM-CIM); SkyWater MPW; FDA SaMD 510(k) guides.
