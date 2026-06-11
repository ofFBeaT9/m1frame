# FINAL REPORT — NEXUS v1.4 "Companion & Interop"

date: 2026-06-11 · pipeline: full m1frame · gates: 1 PASS (5 findings folded), 2 PASS

## The verdict
Cycle 4 closed the council-ranked queue with zero new dependencies (red-team-verified):
- **Per-user Ed25519 attestation keys** (custodial, labelled): all four attestation kinds sign
  with the acting clinician's key; verification resolves the signer and returns their public
  key; cross-user verification provably fails; co-signed notes carry a SECOND verifiable
  signature (attending over author) after the red-team flagged audit-log-only attestation.
- **Commit-flushed NDJSON audit journal** with stitch-verified boot replay — legal-record crash
  window ~0; torn tails tolerated, bad stitches refused.
- **HL7 v2.5 ORU^R01 ingest** into the native lab pipeline (identical critical alerting);
  field indexing red-team-recounted; narrowness honestly labelled (no MLLP/ACK/escapes/SN;
  MRN-existence visibility flagged for production).
- **Portal companion** (advocate queue #1): Help & contact tab (ward phone, visiting hours,
  charge nurse, escalation guidance, emergency contacts) + plain-language diagnosis explainer
  (curated always, AI supplement only when online, labelled).
- **Calculators 24 → 33** (MEWS bands verified against Subbe 2001; PHQ-9 item-9 suicide flag);
  print routes bounce patients to the portal (v1.3 residual retired).

## The evidence
Tests 128 → **149/149**; tsc strict clean both sides; vite build clean; npm ls unchanged;
versions 1.4.0; fmed ff'd to main. Wiki 25 pages, lint 0/0; dashboard 21 nodes / 53 links.

## Faithful process notes
The interop lens agent was spawn-killed by session limits (second cycle running) — its
checklist was self-executed and caught a real defect (locale-dependent canonicalization).
The independent red-team ran fully: PASS WITH CONCERNS → all three items closed, one by
implementation rather than documentation.

## Next steps (cycle 5 queue, ranked)
1. Postgres adapter behind the store choke-point (last substrate item).
2. User-held keys / QES exploration (true non-repudiation).
3. HL7 SN value support + MLLP/ACK if interop deepens.
4. Portal i18n/RTL (spec §15 localization).
