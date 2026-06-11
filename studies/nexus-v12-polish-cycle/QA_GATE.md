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

## Gate 2 — Results review (post-build, post-council, post-red-team)

**Verdict: PASS**

- Build: server tsc strict clean; web tsc strict clean; vite build clean (116 modules).
- Tests: 71 (v1.1) → **103 (v1.2)**, all passing — four new modules (notes/consent/triage/beds),
  six v1.1 residuals each with a regression test, eleven new calculators with worked examples,
  and a regression test for every council finding (G1-G4, E1-E3) and red-team must-fix (MF-1, MF-2).
- Council scores (pre-fix): clinical governance 7.5, engineering 7, clinical UX 6.5 (mid-cycle,
  before the four web pages + polish round landed). All findings folded in-cycle, none caveated.
- Red-team gate CONCERNS → both must-fixes closed with tests/doc corrections.
- Contradictions resolved explicitly: (1) council E2's own proposed fix (read_chart gate) was
  wrong — the patient role's "own" scope is truthy; evidence (a failing test) corrected it to a
  documentation gate, then the red-team tightened it again to write_soap-only when write_vitals
  proved too wide. Two-step correction recorded honestly. (2) UX lens reviewed mid-flight and
  flagged "four missing pages" — resolved by delivery order, recorded as a process note
  (synchronize council snapshots with parallel dev agents, or brief the lens on in-flight work).
- Honest residuals for next cycle: patient portal UI (§14), chat/video (§13), print/PDF (§12),
  imaging (§3.7), HL7 v2 ingest, production substrate (WORM/e-signature/witness hardware).
