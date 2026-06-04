---
title: Ternary Computing
tags: [ternary, quantization, sparsity, efficiency]
related: ["[[Tritone]]", "[[Digital Ternary CIM]]", "[[Optical Processing Unit]]", "[[Bit-Exact Determinism]]"]
created: 2026-06-02
sources: ["opu-feasibility-study", "chip-architecture-council"]
page_type: concept
confidence: high
---

# Ternary Computing

Neural-network weights constrained to **{−1, 0, +1}**. Two consequences drive every hardware choice for
[[Tritone]]:

1. **Multiplier-free.** A "multiply" is just pass / negate / skip; accumulation is add/subtract. → zero DSPs,
   tiny PEs (~20–30 gates), low power, and trivially [[Bit-Exact Determinism|bit-exact]] integer arithmetic.
2. **Sparse.** A τ=0.7 threshold zeros ~42–84 % of weights. A `0` costs nothing to compute and (in
   [[Digital Ternary CIM]]) nothing to read; in the [[Optical Processing Unit]] it is literally *no light path*.

## Why it matters across substrates
- **Digital:** ternary PEs are among the most ASIC-friendly primitives that exist (CUTIE-class designs reach
  PetaOp/s/W on ternary).
- **Analog:** 3 well-separated levels sidestep analog computing's #1 weakness (holding high-precision weights)
  — but, per [[Analog Derivative Fragility]], robustness of *values* does not rescue *derivatives*.

Ternary is the through-line: it's why Tritone is cheap and deterministic, and why it's the recommended
substrate in the [[Chip Manufacturing Decision]].
