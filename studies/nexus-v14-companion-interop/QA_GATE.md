# QA_GATE.md — nexus-v14-companion-interop

## Gate 1 — Roadmap review (pre-build)

**Verdict: PASS (5 findings folded)**

| # | Finding | Disposition |
|---|---------|-------------|
| 1 | Key-scheme swap silently invalidates v1.3 HMAC signatures in old snapshots. | Acceptable for a demo BUT must be explicit: verify reports valid:false with reason "signature scheme upgraded (v1.4)" rather than a bare false; persistence snapshot version stays 1 (shape unchanged — PEM fields are additive); documented in README. |
| 2 | Ed25519 keygen per user on every seed adds boot latency. | Measured risk accepted: 11 keypairs ≈ milliseconds (generateKeyPairSync ed25519 is fast); test asserts seed < 2s stays true implicitly via suite runtime. |
| 3 | Journal replay could double-apply entries already inside the snapshot. | Replay strictly filters seq >= snapshot.audit_log.length AND verifies the stitched chain; a mismatched stitch refuses the journal tail (logged) rather than corrupting the chain. |
| 4 | HL7 OBX values can be non-numeric (coded results); naive Number() would store NaN. | Parser rejects non-numeric OBX-5 for OBX-2=NM and SKIPS non-NM observation types with a warning list in the response — never NaN into the lab pipeline. |
| 5 | Explainer must not block on AI nor leak clinician jargon when AI is up. | Curated text is ALWAYS returned as the base; AI enrichment is appended only when aiOnline() and labelled source:"ai" separately; portal renders curated first. |

Feasibility: confirmed — all single-seam insertions; zero new deps checkable via npm ls.

## Gate 2 — Results review (post-build, post-council, post-red-team)

**Verdict: PASS**

- Build: server tsc strict clean; web tsc strict clean; vite build clean; npm ls UNCHANGED
  (zero-new-deps claim verified by the red-team).
- Tests: 128 (v1.3) → **149 (v1.4)** — per-user key matrix (cross-user fail, legacy reason,
  all four kinds + cosign chain), journal round-trip/torn-tail/kill-the-snapshot, HL7
  happy/critical/malformed/wrong-type/unknown-MRN/role, companion support+explainer
  (offline-fallback proven), 7 calculator worked-example suites.
- Council: interop lens checklist self-executed after a second spawn-kill (recorded) — one
  folded fix (locale-dependent canonicalization → code-unit sort). Red-team ran independently:
  PASS WITH CONCERNS → all three items closed (counts fixed; HL7 enumeration labelled for
  production; co-signature implemented FOR REAL rather than documented away).
- Honest labels verified: custodial keys, journal scope (legal record only), HL7 narrowness
  (now incl. SN/escapes/enumeration).
- Residuals re-scoped for cycle 5: Postgres adapter (last standing substrate item), MLLP/ACK
  transport if interop deepens, user-held keys/QES, HL7 SN value support, portal i18n/RTL.
