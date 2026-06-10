# Chapter: NEXUS v1.2 "Clinical Record & Professional Polish"
date: 2026-06-10
topic: Cycle 2 on fmed — notes engine w/ amendment trail, consent, triage/ESI, beds,
retire all v1.1 residuals, expand calculators, professional/spotless finish.

## Phase 0 — Recall (miras: in-repo records, cycle 1)
Prior decisions binding this cycle:
- Council ranking from v1.1: (1) consent + note amendment trail (medico-legal #1 exposure;
  write_soap permission exists with no notes engine), (2) triage/ESI + bed board (Encounter
  already carries triage_score/triage_system/bed_id), (3) production substrate (OUT — demo-grade
  constraint stands), (4) calculator expansion + NEWS2 medium-band decision.
- Residuals to retire (documented in README/QA_GATE): FHIR $-sigil alias, NEWS2 medium band no
  alert, K+ critical 6.5 → 6.0, witness co-authentication in substance, paracetamol absolute
  adult max, metformin eGFR<30 hard stop.
- Lessons in force: inventory before planning; a silently-passing safety check is worse than
  none; mutation-by-resource-id routes need lookup-then-authorize with 404 cloak; lazy sweeps
  beat schedulers; honest versioning (v1.2.0, not v2.0.0).
No contradictions in memory. Inventory of v1.1 is fresh (built last cycle, in-context).
