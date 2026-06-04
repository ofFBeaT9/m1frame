---
title: FDA SaMD Determinism
tags: [regulatory, fda, samd, 510k, medical]
related: ["[[Bit-Exact Determinism]]", "[[ENS-GI Digital Twin]]", "[[Chip Manufacturing Decision]]"]
created: 2026-06-02
sources: ["chip-architecture-council"]
page_type: concept
confidence: high
---

# FDA SaMD Determinism

Why reproducible inference is a **regulatory prerequisite**, not a nicety, for the clinical
[[ENS-GI Digital Twin]].

## The requirement
FDA AI/ML Software-as-a-Medical-Device doctrine (Jan 2025 draft; Aug 2025 PCCP final) requires:
- a **locked algorithm** at submission with documented performance,
- **reproducible, auditable** inference — same input → same output, every device/run,
- **SBOM** traceability to specific weights + inference code,
- a **Predetermined Change Control Plan**; any weight update → documented re-validation.

## Why it decides the chip
Analog non-determinism (thermal noise, aging, fab variation; the [[Optical Processing Unit]]'s ~7.8 % floor)
**fails 510(k)** — you cannot file "outputs are approximately correct." This functionally disqualifies optics,
charge-domain CIM, and ReRAM for [[Tritone]], and mandates [[Bit-Exact Determinism]] → a fully-digital
[[Digital Ternary CIM]] in the [[Chip Manufacturing Decision]].

## Engineering implication
Weights must load via an auditable boot chain — on-chip OTP or **SHA-256-verified** flash — to preserve the
lock (red-team finding F4).
