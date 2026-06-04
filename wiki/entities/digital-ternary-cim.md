---
title: Digital Ternary CIM
tags: [cim, compute-in-memory, digital, ternary, asic]
related: ["[[Ternary Computing]]", "[[Bit-Exact Determinism]]", "[[Chip Manufacturing Decision]]", "[[SkyWater SKY130 MPW]]"]
created: 2026-06-02
sources: ["chip-architecture-council"]
page_type: entity
confidence: medium
---

# Digital Ternary CIM

The recommended **production** compute style for [[Tritone]]: a **fully-digital** ternary compute-in-memory
macro (bit-serial/parallel accumulation in/near SRAM, **no ADC**). It keeps [[Bit-Exact Determinism]] while
getting much of the efficiency of in-memory compute.

## Why digital, not analog CIM
The council's analog member proposed *charge-domain* SRAM CIM at ~1000–2941 TOPS/W, but the red-team showed
charge-domain CIM accumulates analog charge and reads via ADC → **not bit-exact** → fails
[[FDA SaMD Determinism]] just like the [[Optical Processing Unit]]. Only fully-digital CIM qualifies for the
regulated path.

## Realistic numbers
Digital ternary CIM lands at **~30–150 TOPS/W** (vs the analog ~2941 figure that does *not* apply here) — far
better than the FPGA, fully deterministic, and 510(k)-compatible. Targeted for TSMC 22/28 nm in Phase 2 of the
[[Chip Manufacturing Decision]]. A simpler scaled systolic array is the conservative alternative.
