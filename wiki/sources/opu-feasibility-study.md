---
title: OPU Feasibility Study
tags: [source, simulation, optical, opu_study]
related: ["[[OPU Feasibility Verdict]]", "[[Optical Processing Unit]]", "[[Analog Derivative Fragility]]"]
created: 2026-06-02
page_type: source
confidence: high
---

# OPU Feasibility Study (source)

Summary of an ingested source. Raw artifacts live in `opu_study/` (immutable from the wiki's view).

## What it is
A self-contained software study (numpy, ~29 s) testing whether an analog optical MVM could replace
[[Tritone]]'s ternary MAC: a **bit-exact** integer ternary baseline + a physically-motivated optical-noise
model (additive readout noise by SNR, static weight/phase error, extinction-ratio leakage, crosstalk), swept
over optical SNR, measuring output **value** error and **derivative** (Jacobian) error.

## Key files
- `opu_study/optical_mvm.py` — baseline MAC + `OpticalMVM` model.
- `opu_study/pinn_opu_sim.py` — faithful 7-layer ternary PINN + metrics (INT8 vs smooth-analog path).
- `opu_study/run_study.py` — SNR sweep → `results/{snr_sweep.csv,png,summary.json}`.
- `opu_study/tests/` — 11 passing correctness tests; `FINAL_REPORT.md`, `ROADMAP.md`, `QA_GATE.md`.

## Headline numbers
Sparsity 42.4 %; value error crosses the 19.4 % budget at SNR ≈ 18.2 dB; static-defect floor ≈ 7.8 %;
static 2 % weight defect → value 8.1 % / derivative 51.9 %. Conclusions captured in [[OPU Feasibility Verdict]].
