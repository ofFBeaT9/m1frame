---
title: Bit-Exact Determinism
tags: [determinism, reproducibility, integer, verification]
related: ["[[Tritone]]", "[[FDA SaMD Determinism]]", "[[Analog Derivative Fragility]]", "[[Digital Ternary CIM]]"]
created: 2026-06-02
sources: ["opu-feasibility-study", "chip-architecture-council"]
page_type: concept
confidence: high
---

# Bit-Exact Determinism

The property that the **same input produces exactly the same output**, bit-for-bit, on every chip, at every
temperature, on every run. [[Tritone]] has it by construction (integer [[Ternary Computing]] arithmetic,
verified at 0.00000 error).

## Why it is the crown jewel
- It is the prerequisite for [[FDA SaMD Determinism]] (a locked, auditable algorithm).
- It enables golden-vector verification and a reproducible SBOM.
- It is exactly what **analog** substrates forfeit: the [[Optical Processing Unit]] has a ~7.8 % irreducible
  noise floor, and even "high-efficiency" charge-domain CIM is analog/ADC-based. This single property is why
  the [[Chip Manufacturing Decision]] picks **fully-digital** silicon ([[Digital Ternary CIM]]) over every
  analog option, despite analog's headline TOPS/W.

**Trade:** adopting analog buys efficiency at the cost of determinism — an unacceptable trade for a regulated
medical workload, an acceptable one only in a non-regulated, inference-only, very-large-N pivot.
