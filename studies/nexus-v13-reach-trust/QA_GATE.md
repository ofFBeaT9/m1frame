# QA_GATE.md — nexus-v13-reach-trust

## Gate 1 — Roadmap review (pre-build)

**Verdict: PASS (6 findings folded into the build)**

| # | Finding | Disposition (folded fix) |
|---|---------|--------------------------|
| 1 | Hash-chaining audit entries breaks if ANY code path mutates an already-written entry (e.g. tests editing rows) — false tamper alarms. | Grep confirms nothing mutates audit rows today; verifyAuditChain() reports the first broken seq so genuine test-tampering (the regression test) is distinguishable. Chain computed inside audit() only. |
| 2 | Persistence interval + signal hooks in the test runner would leak timers and make tests order-dependent. | config.persistence defaults to false when NODE_ENV=test or VITEST is set; round-trip test calls save()/load() explicitly — no timers in tests. |
| 3 | Portal endpoints that accept a patient id are one forged id away from cross-patient reads. | Portal routes NEVER read a patient id from the request: the linked patient is resolved server-side from patientUserLinks[req.user.id]; absent link → 403. Test forges ids in body/query and asserts they are ignored. |
| 4 | Chat membership is the new security core; a wrong rule leaks PHI across units. | Membership is ONE function (chatService.canAccessChannel) used by every chat route; tests cover: patient blocked from department + other patients' channels; nurse blocked from other-unit department channel; admin allowed; DM only between the two members. |
| 5 | Signing MAR administrations after the fact (entry mutated post-signature by hold/discontinue flows) would invalidate signatures spuriously. | Signature covers the immutable administration facts only (entry id, drug, dose, route, administered_at/by, witness, waste) — fields that never change after administration; canonicalization is key-sorted. |
| 6 | "Lighter portal identity" could fork the design system. | One wrapper class (`portal`) overriding tokens locally; components reused; no second CSS framework. |

Feasibility: confirmed — every track sits on an existing seam; trust items are single-choke-point
insertions (audit(), three attestation calls). Zero new npm dependencies claimed and checkable.

## Gate 2 — Results review (post-build, post-council, post-red-team)

**Verdict: PASS**

- Build: server tsc strict clean; web tsc strict clean; vite build clean (128 modules).
- Tests: 103 (v1.2) → **128 (v1.3)**, all passing — trust substrate (chain tamper/truncation
  semantics, signature tamper, persistence round-trip + corrupted-snapshot refusal), imaging,
  chat membership matrix, calls lifecycle, portal scoping/forged-id/PHQ-2/access-log/plan,
  release-with-comment, plus regression tests for every advocate finding (P1-P5) and red-team
  must-fix (MF-1, MF-2).
- Council: patient advocate 4.5/10 pre-fix — all five findings folded same-cycle. Security and
  engineering lens AGENTS were killed by a session limit (recorded in council/00-PROCESS-NOTE.md);
  their attack checklists were executed directly and produced three folded fixes (load-time chain
  verification, corrupted-snapshot refusal, tail-truncation honesty + head-hash anchoring). The
  independent red-team then re-attacked everything: CONCERNS → both must-fixes closed.
- Honesty labels verified accurate by the red-team (print/imaging/calls/persistence/signatures).
- Residuals re-scoped out loud for cycle 4: emergency-contact surface + visiting info + plain-
  language diagnosis explainer in the portal; print-route portal redirect; per-user signing keys;
  HL7 v2 ingest; Postgres adapter.
