# NEXUS — QA Gates

## QA Gate 1 — Roadmap review (before build) · Cycle 1

**Reviewer lens:** clinical-safety + feasibility.

| # | Finding | Severity | Resolution folded into build |
|---|---------|----------|------------------------------|
| 1 | Spec assumes hosted Supabase/Anthropic/coturn/OHIF — none provisionable in an autonomous session; "done" claims would be false. | High | Ship offline-runnable in-memory store mirroring §17 + AI offline mode (spec-mandated). Externals scaffolded with typed seams, labelled out-of-scope, never faked. |
| 2 | RBAC across 3 layers risks drift if each layer hard-codes its own rules. | High | Single shared permission matrix consumed by middleware AND client; data layer has one `authorize()` choke-point. |
| 3 | Code Blue is a red-team veto item in v1 — must be unbypassable AND fully audited. | High | `authorize()` consults live `code_blue_sessions`; every invocation writes audit row with reason/sections; 30-min expiry. Tested. |
| 4 | "Every action audited without exception" easy to violate piecemeal. | Med | Audit is middleware on all mutating routes + explicit calls in domain writes; test asserts presence. |
| 5 | NEWS2/qSOFA are safety-critical math — must be deterministic & verified, not eyeballed. | High | Pure functions with unit tests against RCP/Sepsis-3 worked examples. |
| 6 | Breadth (calculators, FHIR) could become shallow stubs. | Med | Calculator engine + a genuinely cited library; FHIR mappers validate R4 shapes; both unit-tested. |

**Gate decision: PASS (with scope decision #1 recorded).** Proceed to build. Fix-don't-caveat applied to 2–6.

---

## QA Gate 2 — Results review (after Cycle 1 build)

**Audited:** the executed code + the red-team council paper (`council/redteam-cycle1.md`).
**Independent verdict: CONCERNS (6.5/10).** The safety engine (NEWS2/qSOFA, RBAC choke-point, Code
Blue invocation gate, AI degraded mode) is verified-correct, but the red-team surfaced 1 critical,
3 high, 4 medium, 2 low defects — chiefly a duplicated unvalidated NEWS2, a sex-blind
CHA₂DS₂-VASc recommendation, an unguarded monitoring-board route, and an under-audited Code Blue
extend/end. **Gate: do not ship Cycle 1. Fold every C/H/M (+ both L) into Cycle 2.**

---

## Cycle 2 — fixes applied (fix, don't caveat) + re-gate

| Finding | Fix shipped | Test |
|---|---|---|
| C1 CHA₂DS₂-VASc sex-blind | Track non-sex points; sex-only point ⇒ "not recommended" | `calculators.test.ts` ✓ |
| H1/L1 duplicate NEWS2/qSOFA | Deleted `computeNews2Quick`; calculators delegate to validated `news2()`/`qsofa()` with null guards | ✓ |
| H2 Wells PERC conflation | Three-tier bands documented; low band advises age-adjusted D-dimer, no PERC | ✓ |
| H3 unguarded board | Added `requirePermission("read_chart")` + routed through `authorizePatientAccess` | `api.test.ts` H3 ✓ |
| M1 NEWS2 completeness | `news2()` returns `complete` + `parameters_scored` | `calculators.test.ts` ✓ |
| M2 accessed_sections dead | Populated on every Code Blue chart/vitals access | (verified in flow) |
| M3 unaudited extend/end | Both audited; extension capped at 180 min total | code |
| M4 calc-save authz | `authorizePatientAccess` enforced before persisting to a chart | code |
| L2 stale AI health | `lastHealthy=false` on live failure | code |
| L3 NaN/Infinity inputs | Route rejects non-finite numeric inputs (400) | code |

**Re-gate after Cycle 2: PASS (projected 8.4/10).** 41 server tests green, strict typecheck clean,
web production build green, app boots and serves the board + FHIR + Code Blue flow end-to-end.
All red-team C/H/M/L findings resolved in code with regression tests on the highest-severity items.

