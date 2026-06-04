# Log

Append-only chronological record. Never delete entries.

## 2026-06-02 — OPU feasibility study ingested
- BMAD cycle 1. Source [[OPU Feasibility Study]] created. New: [[Optical Processing Unit]] (entity),
  [[Analog Derivative Fragility]] (concept), [[OPU Feasibility Verdict]] (synthesis).
- Finding: analog optical MVM keeps output **values** within Tritone's 19.4 % ternary budget at ~18 dB/layer
  SNR, but **derivatives** collapse (~6× more fragile, ε-stable) → optics is **inference-only**.
- Contradiction logged & resolved: a QA sub-agent caught an INT8-staircase artifact inflating the derivative
  metric; fixed by moving to the smooth analog path (clean-Jacobian ε-stability 189 %→3.3 %).

## 2026-06-02 — Chip architecture council ingested
- BMAD cycle 2. Source [[Chip Architecture Council]] created (3 position papers + red-team gate). New:
  [[Digital Ternary CIM]], [[SkyWater SKY130 MPW]] (entities), [[Bit-Exact Determinism]],
  [[FDA SaMD Determinism]] (concepts), [[Chip Manufacturing Decision]] (synthesis),
  [[What Chip Should We Manufacture]] (query).
- Contradiction logged & resolved: Council-2 called charge-domain SRAM CIM "fully deterministic"; the
  red-team showed it is analog/ADC-based (not bit-exact) → resolved in favor of **fully-digital** ternary CIM
  (30–150 TOPS/W) per [[Bit-Exact Determinism]] + [[FDA SaMD Determinism]].
- Verdict: manufacture a fully-digital ternary ASIC, trigger-gated; see [[Chip Manufacturing Decision]].

## 2026-06-03 — m1frame Studio ingested
- BMAD ×2 (build + surpass-Hermes hardening). New: [[m1frame]] (entity), [[m1frame Studio]] (synthesis).
- Shipped a real-time, zero-build UI + an SSE streaming engine (`agents/events.py`, `api/server.py`); made the
  council's **red-team real in code** (`agents/council.py` — it can veto a pass), so the headline differentiator
  is true in the engine, not just the demo.
- Council + red-team fact-check folded in: accessibility (real `<button>`s, reduced-motion, WCAG-AA contrast),
  security (SSRF guard, config-write validation, localhost bind), and claim honesty.
- Contradiction logged & resolved: the synthesis claimed "graph physics paused" under reduced-motion but the
  code didn't; the red-team caught it → fixed (settle-then-freeze). Two reviewer "blockers" (SSE-hang ×2,
  score-ring) were verified **false** and rejected.
- Positioning vs **Hermes Agent**: *not* broadly superior; **decisively ahead on auditable, watchable
  deliberation.** Honest headline: "the most auditable multi-agent workspace there is." See `studies/m1frame-studio/`.

- 2026-06-04 — Ingested [[m1frame Constellation Release]] + saved query [[Is m1frame v1.3 Production Ready]] (v1.3 readiness audit; GO 8.3/10, 90/90 QA).
