---
title: Optical Processing Unit
tags: [optical, photonic, analog, mvm, accelerator]
related: ["[[Tritone]]", "[[Analog Derivative Fragility]]", "[[OPU Feasibility Verdict]]", "[[Ternary Computing]]"]
created: 2026-06-02
sources: ["opu-feasibility-study"]
page_type: entity
confidence: high
---

# Optical Processing Unit

A proposed **analog photonic** matrix-vector-multiply (MVM) layer for [[Tritone]] — MZI mesh or microring
weight bank doing the linear algebra at the speed of light. Ternary is a natural optical fit: +1 → 0-phase,
−1 → π-phase, 0 → blocked (no light path = free sparsity), see [[Ternary Computing]].

## What the study found ([[OPU Feasibility Verdict]])
- **Values survive:** added error stays within the 19.4 % ternary budget down to ~18 dB/layer SNR, but a
  **~7.8 % static-defect floor** remains.
- **Derivatives don't:** a fixed 2 % weight defect → 8.1 % value vs 51.9 % derivative error
  ([[Analog Derivative Fragility]]). Optical **training** is impossible.
- **Verdict:** viable only as an **inference-only** accelerator for a frozen network — and even then loses
  [[Bit-Exact Determinism]]. The [[Chip Manufacturing Decision]] rejects it for this regulated workload.

## Scale caveat
At Tritone's widest layer (512), a 512×512 MZI mesh would need ~262 W of thermo-optic tuning; the photonic
energy win only appears above N≈4096.
