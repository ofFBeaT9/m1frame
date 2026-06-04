# chip_decision/ — "What chip should we manufacture?"

All results from BMAD cycle 2 (the chip-manufacturing decision), saved per request.

| File | What it is |
|---|---|
| **DECISION.md** | The synthesized answer: what to build, phased manufacturing path, trigger gates, the ultimate architecture, and what's rejected + why. **Start here.** |
| `council/01_digital_asic.md` | Council member 1 — digital ternary ASIC case (SKY130 / 28 nm specs, cost, power). |
| `council/02_analog_photonic_inmemory.md` | Council member 2 — photonics vs ReRAM vs SRAM-CIM analog analysis. |
| `council/03_systems_regulatory.md` | Council member 3 — workload, edge deployment, FDA SaMD determinism. |
| `council/04_redteam_qa_gate.md` | Red-team QA gate — caught the charge-domain-CIM determinism error + trigger/SKY130 caveats. |

Related: the optical study that fed this decision lives in `../opu_study/`; the navigable knowledge graph
(entities, concepts, synthesis, the saved query) lives in `../wiki/`. Persistent facts are in **miras**.

**One-line answer:** manufacture a *fully-digital* multiplier-free **ternary ASIC** (SKY130 prototype →
TSMC 28 nm production) for bit-exact, sub-10 mW, FDA-certifiable edge inference — but only once clinical
volume / a sub-5 mW need / a certified-BOM submission triggers it. Determinism beats TOPS/W here.
