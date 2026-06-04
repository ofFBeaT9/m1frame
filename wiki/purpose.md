# Purpose

The soul of this wiki. The LLM reads this on every operation.

## Domain
Hardware-acceleration strategy for **[[Tritone]]** — a multiplier-free **ternary** neural-network
accelerator that runs a Physics-Informed Neural Network (PINN) for the **[[ENS-GI Digital Twin]]**
(a clinical GI / enteric-nervous-system model).

## Questions we are trying to answer
1. Can an exotic compute substrate (optical, analog in-memory) accelerate Tritone without destroying the
   PINN accuracy that justifies it? → answered in **[[OPU Feasibility Verdict]]**.
2. **What chip should we actually manufacture, and what is the ultimate computing architecture?** →
   answered in **[[Chip Manufacturing Decision]]** / **[[What Chip Should We Manufacture]]**.

## Evolving thesis
For a **regulated, edge, small-N medical** workload, **determinism dominates raw efficiency.** The optimum
is a **fully-digital, bit-exact ternary ASIC** for frozen-model inference, with training kept in the cloud
where exact gradients survive. Analog substrates (photonic, charge-domain CIM, ReRAM) are disqualified by
**[[Analog Derivative Fragility]]** and **[[FDA SaMD Determinism]]** for *this* workload.

## Sources in scope
The **[[OPU Feasibility Study]]** (software simulation) and the **[[Chip Architecture Council]]**
(3 specialist position papers + a red-team gate). Both are summarized as immutable source pages; the
structured knowledge sits in the entity/concept/synthesis layers above them.
