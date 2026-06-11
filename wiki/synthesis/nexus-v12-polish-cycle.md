---
title: NEXUS v1.2 Polish Cycle
tags: [synthesis, nexus, clinical-record, polish, decision]
related: ["[[NEXUS Clinical Platform]]", "[[NEXUS v2 Gap Cycle]]", "[[Residual Retirement]]", "[[Clinical Safety Loops]]", "[[Can One Cycle Make NEXUS Spotless]]", "[[m1frame]]"]
created: 2026-06-11
sources: ["nexus-v2-master-prompt"]
page_type: synthesis
confidence: high
---

# NEXUS v1.2 Polish Cycle

**The verdict:** cycle 2 of the [[NEXUS Clinical Platform]] made the clinical record legally
shaped and the product professionally detailed: a notes engine (finalize lock, append-only
addenda, resident co-sign with a machine-enforced 24h overdue sweep), consent management
(witnessed templates, mandatory completion), ESI triage (handbook-aligned danger zones, mandatory
override reasons, ESI-1 critical alerts), bed management (single-writer rule), all six v1.1
residuals retired per [[Residual Retirement]], calculators 13 → 24, and a two-round web build
(four new surfaces + a six-item polish pass: patient banners, deep links, role-aware landing,
admin completeness). Shipped as v1.2.0 with **103/103 tests**, strict TS and builds clean.

## What the council and red-team caught (and the cycle fixed)
- **ESI undertriage** — danger-zone thresholds were looser than the AHRQ v4 handbook (SpO₂ <85
  vs <90; HR missing entirely). A triage engine that undertriages is the same failure class as a
  silently-passing allergy check. Fixed with per-threshold regression assertions.
- **The council can be wrong too:** the engineering lens prescribed a `read_chart` gate for
  consent templates — but the patient role's "own" chart scope is truthy, so the gate wouldn't
  exclude patients. A failing test caught it; the red-team then tightened the corrected gate
  again (write_vitals admitted med_tech). Lesson: *council recommendations are hypotheses;
  tests are the arbiter.*
- Stale README counts, a fragile FHIR middleware ordering (now a documented ORDERING CONTRACT),
  and six UX gaps (silent 403 landings, siloed navigation) — all folded in-cycle.

## Open for cycle 3
Patient portal UI (§14, the most underserved persona), chat/video (§13), print/PDF (§12),
imaging (§3.7), HL7 v2 ingest, production substrate (WORM audit, e-signature, witness hardware).
