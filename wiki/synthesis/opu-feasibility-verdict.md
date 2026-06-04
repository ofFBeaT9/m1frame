---
title: OPU Feasibility Verdict
tags: [optical, verdict, inference-only, pinn, bmad]
related: ["[[Optical Processing Unit]]", "[[Analog Derivative Fragility]]", "[[Tritone]]", "[[Chip Manufacturing Decision]]"]
created: 2026-06-02
sources: ["opu-feasibility-study"]
page_type: synthesis
confidence: high
---

# OPU Feasibility Verdict

**Cross-source conclusion** of BMAD cycle 1 (the [[OPU Feasibility Study]]).

## Verdict
An [[Optical Processing Unit]] for [[Tritone]] is **GO only as an inference-only accelerator** for a frozen,
pre-trained ternary PINN; **NO-GO** for optical training / gradients / sensitivity.

## Evidence
- **Values survive:** added value error stays within the 19.4 % ternary budget down to **~18 dB/layer** optical
  SNR (within ONN literature 15–25 dB), with a **~7.8 % static-defect floor** more power can't remove.
- **Derivatives die:** a fixed 2 % weight defect → 8.1 % value vs 51.9 % derivative error
  ([[Analog Derivative Fragility]]); derivative error never reaches the budget.

## Consequence for hardware
Keep training electronic/cloud; deploy only frozen inference. And since even optical inference loses
[[Bit-Exact Determinism]], the [[Chip Manufacturing Decision]] keeps the compute **digital**. Optics would
only be worth revisiting in a non-regulated, inference-only, N≫4096 pivot.

## Provenance note
An independent QA sub-agent caught an INT8-quantization-staircase artifact inflating the original derivative
metric; it was fixed (smooth analog path; clean-Jacobian ε-stability 189 %→3.3 %), strengthening rather than
weakening the verdict.
