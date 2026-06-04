---
title: Analog Derivative Fragility
tags: [analog, noise, derivatives, pinn, gradients]
related: ["[[Optical Processing Unit]]", "[[OPU Feasibility Verdict]]", "[[Bit-Exact Determinism]]"]
created: 2026-06-02
sources: ["opu-feasibility-study"]
page_type: concept
confidence: high
---

# Analog Derivative Fragility

The finding that **analog noise corrupts a network's derivatives far more than its values** — decisive for a
Physics-Informed Neural Network, whose usefulness depends on `d(output)/d(input)`.

## Evidence ([[OPU Feasibility Verdict]])
- Output **values** of [[Tritone]]'s PINN stay within the 19.4 % ternary budget down to ~18 dB/layer optical
  SNR.
- **Derivatives** do not: a fixed 2 % photonic weight defect (zero shot noise) gives 8.1 % value error but
  **51.9 % derivative error** — an ε-stable ~6× gap, not a numerical artifact.

## Consequence
- Analog substrates can do **inference** of values but cannot support **training / gradients / sensitivity**.
- Therefore training stays in the cloud (exact gradients) and only frozen inference is deployed — and even
  inference loses [[Bit-Exact Determinism]]. This is the physics half of why the [[Chip Manufacturing Decision]]
  rejects the [[Optical Processing Unit]] (the regulatory half is [[FDA SaMD Determinism]]).

## Method caveat
Measured via finite-difference Jacobians; the *absolute* amplification scales ~1/ε, so the robust evidence is
the ε-stable static-defect gap, not the bare factor (a QA sub-agent caught and corrected the original metric).
