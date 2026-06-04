---
title: Tritone
tags: [accelerator, ternary, fpga, pinn, hardware]
related: ["[[Ternary Computing]]", "[[ENS-GI Digital Twin]]", "[[Bit-Exact Determinism]]", "[[Chip Manufacturing Decision]]", "[[Optical Processing Unit]]"]
created: 2026-06-02
sources: ["chip-architecture-council", "opu-feasibility-study"]
page_type: entity
confidence: high
---

# Tritone

A **multiplier-free ternary** neural-network inference accelerator. Weights ∈ {−1,0,+1}, so a MAC is just
a mux + conditional add — **zero hardware multipliers, zero DSP blocks** (see [[Ternary Computing]]). It runs
a 7-layer Physics-Informed Neural Network (PINN) for the [[ENS-GI Digital Twin]].

## Current implementation
- Board: Tang Nano 9K FPGA (Gowin GW1NR-9C, 27 MHz), ~$20.
- 16×16 systolic processing-element array, 0 DSP, 5088 LUT, **~105 mW**, runs the PINN **bit-exact**
  (0.00000 error) — its defining property, [[Bit-Exact Determinism]].
- PINN: 110 inputs → 512→512→512→128→128→128 (with residual/skip) → 5 sigmoid outputs (ion-channel
  conductances). ~42 % of weights are zero; ternarization already costs 19.4 % mean rel error.

## Strategic position
- The [[Optical Processing Unit]] study showed analog substrates can't replace it for training (see
  [[Analog Derivative Fragility]]).
- The [[Chip Manufacturing Decision]] recommends taking Tritone to a fully-digital ternary ASIC
  ([[Digital Ternary CIM]]) — prototyped on [[SkyWater SKY130 MPW]] — rather than any analog path.
