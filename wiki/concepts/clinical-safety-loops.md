---
title: Clinical Safety Loops
tags: [concept, patient-safety, prioritization, clinical]
related: ["[[NEXUS Clinical Platform]]", "[[NEXUS v2 Gap Cycle]]", "[[Premature Decomposition]]"]
created: 2026-06-10
sources: ["nexus-v2-master-prompt"]
page_type: concept
confidence: high
---

# Clinical Safety Loops

A prioritization heuristic for clinical software: **close the loops where hospitals actually harm
or save patients before adding surface breadth.** A "loop" is a workflow that is unsafe when any
link is missing — implementing half of it earns no safety credibility.

The three core loops (as shipped in the [[NEXUS Clinical Platform]] v1.1 cycle):

1. **Medication loop** — order entry → safety checks (allergy/interaction/dose/renal/duplicate,
   with hard-stop / soft-stop-with-override semantics) → MAR administration (witnessed for
   controlled substances, five-rights confirmed, every transition audited).
2. **Results loop** — result entry → reference-range flagging → critical-value alert →
   acknowledgement with read receipt → timed escalation if unacknowledged.
3. **Continuity loop** — structured handover (I-PASS) → receiver synthesises understanding →
   timestamped acceptance → overdue detection.

Counterpoint to feature-matrix thinking: triage boards, bed maps and portals *demo* well but each
is severable — omitting them degrades convenience, not safety. The loops are not severable. This is
the clinical cousin of avoiding [[Premature Decomposition]]: depth at the point of risk first,
breadth on real triggers later. Verdict and evidence: [[NEXUS v2 Gap Cycle]].
