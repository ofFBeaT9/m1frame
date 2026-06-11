---
title: NEXUS v1.4 Companion and Interop Cycle
tags: [synthesis, nexus, interop, trust, companion, decision]
related: ["[[NEXUS Clinical Platform]]", "[[NEXUS v1.3 Reach and Trust Cycle]]", "[[Honest Scope Labels]]", "[[Residual Retirement]]", "[[m1frame]]"]
created: 2026-06-11
sources: ["nexus-v2-master-prompt"]
page_type: synthesis
confidence: high
---

# NEXUS v1.4 Companion and Interop Cycle

**The verdict:** cycle 4 of the [[NEXUS Clinical Platform]] turned the portal from informative
into companioning, and hardened the two trust labels that mattered most — all with zero new
dependencies (claim red-team-verified via npm ls):
- **Per-user Ed25519 attestation keys** (custodial, honestly labelled): every note, consent,
  MAR administration and radiology report signs with the ACTING clinician's key; verification
  resolves the signer and returns their public key; cross-user verification provably fails.
  After the red-team, **co-signatures became real**: the attending mints a second signature
  over the author's, so the attestation chain verifies end-to-end on the artifact.
- **Audit journal**: NDJSON flushed at commit; boot stitches the journal tail onto the snapshot
  and re-verifies the chain — the legal record's crash window is ~0.
- **HL7 v2.5 ORU^R01 ingest** feeding the native lab pipeline (critical values alert
  identically), with narrowness stated per [[Honest Scope Labels]] (no MLLP/ACK/escapes/SN,
  MRN-existence visibility flagged for production).
- **Portal Help & contact**: ward phone, visiting hours, escalation guidance, emergency
  contacts, and a plain-language diagnosis explainer (curated always, AI supplement only when
  online, labelled). Calculators 24 → 33. Shipped v1.4.0, **149/149 tests**.

## What the adversarial process caught
- Self-executed interop checklist (the lens agent was spawn-killed by session limits twice —
  recorded faithfully): **locale-dependent canonicalization** in the signing payload
  (localeCompare) could have broken cross-host re-verification — replaced with code-unit sort.
- Red-team (ran independently, PASS WITH CONCERNS → resolved): stale calculator counts; the
  co-signer attestation living only in the audit log — fixed by implementation, not
  documentation, per [[Residual Retirement]]'s spirit; MRN enumeration via the HL7 route
  accepted-with-label as the same hospital-wide trade-off as native lab entry.

## Open for cycle 5 (re-scoped out loud)
Postgres adapter (last substrate item), MLLP/ACK transport, user-held keys/QES, HL7 SN values,
portal i18n/RTL.
