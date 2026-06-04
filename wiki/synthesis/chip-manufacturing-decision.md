---
title: Chip Manufacturing Decision
tags: [decision, asic, manufacturing, ternary, bmad]
related: ["[[Tritone]]", "[[Digital Ternary CIM]]", "[[SkyWater SKY130 MPW]]", "[[Bit-Exact Determinism]]", "[[FDA SaMD Determinism]]", "[[OPU Feasibility Verdict]]", "[[What Chip Should We Manufacture]]"]
created: 2026-06-02
sources: ["chip-architecture-council", "opu-feasibility-study"]
page_type: synthesis
confidence: high
---

# Chip Manufacturing Decision

**The cross-source conclusion** of BMAD cycle 2 (a 3-member [[Chip Architecture Council]] + red-team),
informed by the [[OPU Feasibility Verdict]].

## Decision
Manufacture a **fully-digital, multiplier-free ternary ASIC** ([[Digital Ternary CIM]] or scaled systolic
array) that preserves [[Tritone]]'s [[Bit-Exact Determinism]]. **Not** analog, photonic, or charge-domain CIM.

| Phase | What | Where | Trigger |
|---|---|---|---|
| 0 (now) | stay on FPGA + Cortex-M33 | Tang Nano 9K | — (default) |
| 1 | 64×64 digital ternary systolic array (validation vehicle) | [[SkyWater SKY130 MPW]] (~$10–12k) | a tape-out trigger fires |
| 2 | fully-digital ternary CIM + Cortex-M33 host | TSMC 22/28 nm (~30–150 TOPS/W) | clinical production |

**Tape-out triggers (need ≥1):** >~500 clinical units, **or** a <5 mW envelope the FPGA can't meet, **or** a
regulatory submission requiring a certified silicon BOM. Until then, do not spend NRE.

## The ultimate architecture
A **lifecycle**, not a single chip: *cloud-train (exact gradients, the physics residual) → freeze + certify
(golden vectors, SHA-256 weight lock, SBOM, 510(k)) → edge bit-exact ternary inference (sub-10 mW)*. This split
is forced by [[Analog Derivative Fragility]] (gradients can't live on noisy hardware) and
[[FDA SaMD Determinism]] (inference must be reproducible).

## Why (the contradiction it resolves)
Analog promises higher TOPS/W, but every analog option forfeits [[Bit-Exact Determinism]]: the
[[Optical Processing Unit]] has a 7.8 % floor; charge-domain CIM is ADC-based (red-team F1); ReRAM is immature.
For a **regulated, edge, small-N** workload, *determinism dominates efficiency* — so digital ternary is the
global optimum. Full reasoning: `chip_decision/DECISION.md`.
