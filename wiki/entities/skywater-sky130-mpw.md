---
title: SkyWater SKY130 MPW
tags: [fab, mpw, open-pdk, 130nm, prototype]
related: ["[[Chip Manufacturing Decision]]", "[[Tritone]]", "[[Digital Ternary CIM]]"]
created: 2026-06-02
sources: ["chip-architecture-council"]
page_type: entity
confidence: high
---

# SkyWater SKY130 MPW

The low-cost, **open-PDK** 130 nm multi-project-wafer shuttle (via Efabless/Google/Cadence) recommended for
**Phase 1** of the [[Chip Manufacturing Decision]].

## Role: prototype / validation vehicle only
- NRE ~**$10–12k**, ~10 mm² slot, ~July 2026 delivery, 20–40 packaged samples.
- Purpose: validate the ternary datapath, the **bit-exact MAC chain** ([[Bit-Exact Determinism]]), and the
  golden-vector test rig for [[Tritone]].
- **Not a production proxy** (red-team F3): 130 nm @ ~200 MHz, ~5 mm² die — power/area/timing do **not**
  transfer to the 28 nm Phase-2 [[Digital Ternary CIM]]. Don't extrapolate its 40 mW / 8 GOPS estimates.

A 64×64 digital ternary systolic array fits comfortably in one slot.
