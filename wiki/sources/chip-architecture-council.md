---
title: Chip Architecture Council
tags: [source, council, redteam, chip_decision]
related: ["[[Chip Manufacturing Decision]]", "[[Digital Ternary CIM]]", "[[SkyWater SKY130 MPW]]", "[[FDA SaMD Determinism]]"]
created: 2026-06-02
page_type: source
confidence: high
---

# Chip Architecture Council (source)

Summary of an ingested source. Raw artifacts in `chip_decision/council/` (immutable from the wiki's view).

## What it is
Four specialist position papers produced to answer *"what chip should we manufacture?"* for [[Tritone]]:
1. **Digital ASIC architect** — SKY130 64×64 ternary systolic array (see [[SkyWater SKY130 MPW]]).
2. **Analog / photonic / in-memory architect** — rejects photonics (7.8 % floor, 262 W tuning) & ReRAM
   (immature); proposed charge-domain SRAM CIM.
3. **Systems / regulatory architect** — edge + cloud-train + frozen inference; [[FDA SaMD Determinism]] anchor.
4. **Red-team QA gate** — caught that charge-domain CIM is analog/ADC (not bit-exact) → corrected to
   [[Digital Ternary CIM]]; gated tape-out behind explicit triggers; SHA-256 weight lock.

## Net effect
Three lenses (silicon, physics, regulation) converged on a deterministic digital ternary chip; the one analog
dissent was self-disqualified. Synthesized in [[Chip Manufacturing Decision]] / `chip_decision/DECISION.md`.
