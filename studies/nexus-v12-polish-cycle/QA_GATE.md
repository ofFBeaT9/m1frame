# QA_GATE.md — nexus-v12-polish-cycle

## Gate 1 — Roadmap review (pre-build)

**Verdict: PASS (5 findings folded into the build)**

| # | Finding | Disposition (folded fix) |
|---|---------|--------------------------|
| 1 | Witness co-auth via password breaks BOTH existing controlled-substance MAR tests; silently editing them would mask a behaviour change. | The two assertions update IN THE SAME story as the fix (S5), with a new negative test (wrong witness password → 422) proving the mechanism. Documented in the commit message. |
| 2 | NEWS2 medium-band alerts will fire during seed (several patients sit at NEWS2 5–6), inflating unack counts the demo board displays. | Accepted clinically (that's the point of the fix) BUT seed acknowledges non-teaching alerts for stable patients so the demo board still highlights the deteriorating patient. Deterministic, documented in seed. |
| 3 | ESI auto-suggestion could be read as diagnostic AI. | esi.ts is a pure rules table citing the ESI v4 handbook; the API response carries "suggested" + mandatory nurse confirm/override — never auto-final. UI labels it "suggested". |
| 4 | Bed transfer must not strand Encounter.bed_id (two sources of truth). | bedService is the ONLY writer of both Bed.current_patient_id and Encounter.bed_id (single-writer rule); test asserts they never diverge across assign→transfer→release. |
| 5 | "Spotless" risks scope creep into the deferred breadth (portal, chat, imaging). | Out-of-scope list is explicit in the PRD; "spotless" defined as: zero documented-but-unfixed defects + all gates PASS + professional surfaces — not feature completeness vs spec v2. |

Feasibility: confirmed — no seam changes; ~4 new route files, 4 services, 1 pure domain module,
additive RBAC columns; web agent pattern proven in cycle 1.
