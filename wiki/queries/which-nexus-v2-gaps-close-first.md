---
title: Which NEXUS v2 Gaps Close First
tags: [query, nexus, prioritization]
related: ["[[NEXUS v2 Gap Cycle]]", "[[Clinical Safety Loops]]", "[[NEXUS Clinical Platform]]"]
created: 2026-06-10
sources: ["nexus-v2-master-prompt"]
page_type: query
confidence: high
---

# Which NEXUS v2 Gaps Close First

**Saved question:** the fmed repo holds NEXUS v1; the v2 Master Build Prompt specifies far more
(MAR, CPOE checks, labs, handover, triage, beds, consent, portal…). Which gaps should one
single-developer, demo-grade upgrade cycle close first to maximize clinical-safety credibility
without rewriting v1's architecture?

**Answer:** close the three [[Clinical Safety Loops]] — medication (CPOE safety checks + MAR with
controlled-substance witness), results (critical-value alert/ack/escalation), continuity (I-PASS
handover) — and defer triage, beds, consent and portal to the next cycle. Executed and proven in
[[NEXUS v2 Gap Cycle]]: v1.1.0 of the [[NEXUS Clinical Platform]], 71/71 tests, both red-team
vetoes now closed in code. Caveat: an inventory-first pass showed one "gap" (Code Blue override)
was already implemented — always audit the codebase before trusting a spec's gap list.
