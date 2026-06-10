---
title: NEXUS v2 Gap Cycle
tags: [synthesis, nexus, prioritization, safety, decision]
related: ["[[NEXUS Clinical Platform]]", "[[NEXUS v2 Master Prompt]]", "[[Clinical Safety Loops]]", "[[Which NEXUS v2 Gaps Close First]]", "[[m1frame]]", "[[MVP Architecture Decision]]"]
created: 2026-06-10
sources: ["nexus-v2-master-prompt"]
page_type: synthesis
confidence: high
---

# NEXUS v2 Gap Cycle

**The verdict:** in one single-developer, demo-grade upgrade cycle of the [[NEXUS Clinical Platform]],
close the three [[Clinical Safety Loops]] — medication (CPOE safety checks → MAR with witness
protocol), results (lab critical-value alert → ack → 30-min escalation), continuity (I-PASS
handover with receiver synthesis) — and **defer breadth** (triage/ESI, bed board, consent workflow,
patient portal). Shipped as v1.1.0 with 71/71 tests green, every new safety transition audited,
FHIR `$everything` now carrying real MedicationRequests and lab Observations.

## Why this ranking won
- It closed the only **open red-team veto** (MAR underspecification) from the
  [[NEXUS v2 Master Prompt]] history.
- Loops are non-severable safety chains; deferred items are severable conveniences — credibility
  per unit of effort favoured depth (cf. [[MVP Architecture Decision]]: same depth-before-breadth
  logic, different domain).
- Everything reused v1 seams (single RBAC matrix, store choke-point, audit-everything, lazy sweeps
  instead of schedulers) — no architectural rewrite, falsifiable by the diff.

## Contradiction tracked (source vs code)
The spec's metadata listed red-team veto #1 ("Code Blue override") as a v2-to-fix item, but the v1
codebase **already implemented it fully** (privilege ≥6 gate, 30-min audited session, 180-min extend
cap). Grounding the cycle in a code inventory before planning prevented rebuilding an existing
feature. Lesson: *spec self-history is testimony; the codebase is evidence — inventory first.*

## Open items for the next cycle
Triage/ESI workflow, bed & ward management, consent capture, patient portal UI, notes engine with
co-sign dashboards, imaging module, calculator-suite expansion. Highest-risk single gap per council
review: end-to-end **consent + notes amendment trail** (medico-legal exposure), with triage second.
