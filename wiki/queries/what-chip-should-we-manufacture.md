---
title: What Chip Should We Manufacture
tags: [query, decision, chip]
related: ["[[Chip Manufacturing Decision]]", "[[Digital Ternary CIM]]", "[[Bit-Exact Determinism]]"]
created: 2026-06-02
sources: ["chip-architecture-council", "opu-feasibility-study"]
page_type: query
confidence: high
---

# Query: What chip should we manufacture? What is the ultimate computing system?

## Answer
Manufacture a **fully-digital, multiplier-free ternary ASIC** — [[SkyWater SKY130 MPW]] prototype (validation
vehicle) → TSMC 28 nm **[[Digital Ternary CIM]]** production + Cortex-M33 host — preserving
[[Bit-Exact Determinism]]. **Don't tape out until** clinical volume (>~500 units), a sub-5 mW need, or a
certified-BOM regulatory submission triggers it; until then the $20 FPGA + an MCU is correct.

**The ultimate system is a lifecycle:** cloud-train (exact gradients) → freeze + certify (golden vectors,
SHA-256 weight lock, SBOM) → edge bit-exact ternary inference (sub-10 mW, 510(k)-certifiable).

**Why not analog:** photonics, charge-domain CIM, and ReRAM all forfeit determinism (see
[[Analog Derivative Fragility]] + [[FDA SaMD Determinism]]); for this regulated, edge, small-N workload
**determinism dominates efficiency**. Full reasoning in [[Chip Manufacturing Decision]].

## One-line
The best computing system here isn't the highest TOPS/W — it's the cheapest **deterministic** one that clears
the medical bar, and that is digital ternary silicon.
