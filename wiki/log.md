# Log

Append-only chronological record. Never delete entries.

- 2026-06-04 — Initialized the starter knowledge graph: framework pages ([[m1frame]], [[m1frame Studio]],
  [[m1frame Constellation Release]]) + the bundled demo ([[MVP Architecture Decision]], [[Modular Monolith]],
  [[Microservices]], [[Conway's Law]], [[Premature Decomposition]]) + the saved query
  [[Is m1frame v1.3 Production Ready]]. Lint clean (0 errors / 0 orphans). Point m1frame at your own domain and
  append your ingests below.
- 2026-06-10 — Ingested [[NEXUS v2 Master Prompt]] (raw → raw/sources, immutable) + the executed
  v1.1 "Safety Loops" cycle: new pages [[NEXUS Clinical Platform]], [[Clinical Safety Loops]],
  [[NEXUS v2 Gap Cycle]], [[Which NEXUS v2 Gaps Close First]]. Contradiction tracked: spec metadata
  listed Code Blue veto as open; v1 code already implements it (inventory-first lesson). fmed bumped
  to 1.1.0, 66/66 tests green. Study artifacts: studies/nexus-v2-gap-cycle/.
- 2026-06-10 — Red-team pass (gate: CONCERNS → resolved): fixed MF-1 (README test count), MF-2
  (med_tech could not reach the lab-entry UI), MF-3 (403/404 existence oracle on order/MAR
  mutation routes → 404 cloak), MF-4 (lab-entry hospital-wide scope now documented + tested).
  Final: 71/71 tests green. Wiki pages corrected from the stale 66 count.
- 2026-06-11 — Cycle 2 ingested: [[NEXUS v1.2 Polish Cycle]] (synthesis), [[Residual Retirement]]
  (concept), [[Can One Cycle Make NEXUS Spotless]] (query); [[NEXUS Clinical Platform]] updated to
  v1.2 state (notes/consent/triage/beds, six residuals retired, 24 calculators, 103/103 tests).
  Contradiction tracked: the engineering council's own gate prescription (read_chart) was wrong for
  the patient role; corrected twice via tests — reviewer prescriptions are hypotheses, tests arbitrate.
  Study artifacts: studies/nexus-v12-polish-cycle/.
- 2026-06-11 — Cycle 3 ingested: [[NEXUS v1.3 Reach and Trust Cycle]] (synthesis),
  [[Honest Scope Labels]] (concept), [[Can a Demo Earn Trust]] (query); [[NEXUS Clinical Platform]]
  updated to v1.3 (portal/chat/imaging/print + WORM chain + e-signatures + persistence; 128/128).
  Process honesty: two council lens agents killed by a session limit — checklists executed directly,
  failure recorded in the study. Red-team caught a forged-urgent-flag path and a stale README count;
  both fixed with tests. Study artifacts: studies/nexus-v13-reach-trust/.
- 2026-06-11 — Cycle 4 ingested: [[NEXUS v1.4 Companion and Interop Cycle]] (synthesis);
  [[NEXUS Clinical Platform]] updated to v1.4 (per-user Ed25519 + verifiable cosign chains,
  commit-flushed audit journal, HL7 ORU ingest, portal Help/explainer, 33 calculators; 149/149).
  Lens agent spawn-killed twice by session limits (checklist self-executed, recorded); its key
  catch — locale-dependent signature canonicalization — was folded. Red-team PASS WITH CONCERNS
  → resolved, incl. implementing co-signatures for real instead of documenting their absence.
  Study artifacts: studies/nexus-v14-companion-interop/.
