# Overview

Auto-regenerated global summary. Human may edit.

## The story so far
**[[Tritone]]** is a multiplier-free **[[Ternary Computing|ternary]]** accelerator running a PINN for the
**[[ENS-GI Digital Twin]]**, today bit-exact on a $20 FPGA. Two questions were investigated via BMAD:

1. **Exotic substrates?** The **[[Optical Processing Unit]]** idea was tested in software
   ([[OPU Feasibility Study]]). Result ([[OPU Feasibility Verdict]]): analog optics preserves output
   **values** at realistic SNR but destroys **derivatives** ([[Analog Derivative Fragility]]) — so it is
   *inference-only* at best.

2. **What to manufacture?** A specialist council ([[Chip Architecture Council]]) plus a red-team converged
   on the **[[Chip Manufacturing Decision]]**: a **fully-digital, bit-exact ternary ASIC**
   ([[Digital Ternary CIM]]), prototyped cheaply on **[[SkyWater SKY130 MPW]]** and produced in TSMC 28 nm —
   *not* analog, because **[[Bit-Exact Determinism]]** is an **[[FDA SaMD Determinism|FDA prerequisite]]**.

## Thesis
For a regulated, edge, small-N medical workload, **determinism dominates efficiency**. Tritone's ternary
design — originally chosen to avoid multipliers — is also the optimal substrate for the regulatory reality.
The "best computing system" is a **lifecycle**: cloud-train (gradients) → freeze + certify → edge bit-exact
inference. Manufacture only when clinical volume / a sub-5 mW need / a certified-BOM submission triggers it.
