# ROADMAP — NEXUS v1.4 "Companion & Interop"

## 1. Analyst — Brief
**Problem.** Three asymmetries remain: the portal informs but doesn't COMPANION (no "who do I
call", no visiting info, no plain-language diagnosis); the trust substrate signs everything with
ONE server key (attribution rests on a shared secret); the legal record tolerates a 10s crash
window; and the lab pipeline only accepts NEXUS-native input (no standards ingest).
**Anchors.** services/ai.ts already has an `education` use case with degraded mode; Unit/Patient
types are the natural carriers for visiting info/emergency contacts; signatures.ts is the single
signing choke-point (one-file swap); store.audit() is the single journal hook; enterLabPanel is
the single lab inlet HL7 should feed.
**Hypothesis.** All six items are single-seam insertions; the riskiest (key migration) is safe
because every signed artifact records its signer id, so verification can resolve the signer's
public key without schema gymnastics.

## 2. PM — PRD
- FR1 Companion: GET /portal/support (unit contact phone + visiting hours + escalation guidance
  + emergency contacts on file); GET /portal/explainer (plain-language diagnosis explainer:
  curated offline text for seeded diagnoses, AI-enriched when online, source labelled);
  Patient += emergency_contacts; Unit += visiting_hours/contact_phone; portal Help surfaces.
- FR2 Per-user keys: Ed25519 keypair per user (node:crypto, custodial PEMs on the User record);
  all four attestation kinds sign with the ACTOR's private key; /verify/:kind/:id verifies
  against the signer's public key and returns signer + public key; honest custodial label.
- FR3 Audit journal: append-only NDJSON written AT COMMIT for every audit entry (enabled with
  persistence); on boot, journal tail beyond the snapshot is replayed and the chain re-verified —
  the legal record's crash window goes to ~0.
- FR4 HL7 v2.5 ORU^R01 ingest: dep-free parser (MSH/PID/OBR/OBX) → existing enterLabPanel
  pipeline (flags/critical alerts fire identically); POST /labs/import/hl7 (upload_labs);
  malformed/non-ORU/unknown-MRN rejected with specific errors; sample-message tests incl. a
  critical K+ raising the alert.
- FR5 Calculators +9 cited (PERC, MEWS, Braden, Morse Fall, GAD-7, PHQ-9, Holliday-Segar,
  BSA Mosteller, IBW Devine+adjusted) → 33 total, worked-example tests.
- FR6 Print routes bounce patient role to /portal (red-team residual).
- NFRs: zero new npm deps; strict TS; all 128 v1.3 tests pass (signature tests updated WITH the
  scheme change, documented); ≥145 total tests; README honesty table updated.
**Out of scope:** non-custodial keys (user-held), HL7 ADT/ORM messages, MLLP transport,
Postgres adapter (still the documented seam), portal i18n.

## 3. Architect (falsifiable)
- types: User += signing_public_key_pem/signing_private_key_pem (custodial); Patient +=
  emergency_contacts[]; Unit += visiting_hours, contact_phone.
- domain/signatures.ts: signAs(privatePem, kind, id, content) / verifyBy(publicPem, ...) via
  crypto.sign/verify(null, …, ed25519). Attestation sites pass the acting user's key; the
  signer id ALREADY stored per artifact (author_id / physician_id / administered_by_id /
  reported_by_id) resolves the public key at verify time. trust.ts returns {signed, valid,
  signer, signer_public_key}.
- db/auditJournal.ts: append(row, path), readAll(path), repair logic; store.audit() appends when
  config.persistence.enabled; persistence.load() replays journal tail (seq >= snapshot length)
  then re-verifies the chain; journal path config.persistence.journalFile.
- domain/hl7.ts: parseOru(message) → {mrn, panel_name, analytes[], message_control_id}; strict
  on MSH-9=ORU^R01; tolerant of \r/\n/\r\n. routes/labs.ts: POST /labs/import/hl7.
- portalService: portalSupport(), portalExplainer() (OFFLINE_EXPLAINERS map keyed by seeded
  primary_diagnosis; runAi("education") enrich when aiOnline()).
- Web (self-built this cycle — small): portal Help tab (support card + explainer), Labs HL7
  import box (upload_labs), App.tsx ProtectedDoc patient bounce.
**Falsifiable:** (a) `npm ls --depth=0` unchanged; (b) a doc signed by user A fails verification
against user B's key (test); (c) kill-the-snapshot test: journal alone reconstructs the audit
log; (d) HL7 K+ 6.8 fires the SAME critical_lab alert path as native entry.

## 4. Scrum Master — stories
S1 keys+signatures swap (+tests: cross-user verify fails, tamper fails, all four kinds).
S2 audit journal (+tests: append/replay, snapshot-behind-journal recovery, chain valid).
S3 HL7 parser+route (+tests: happy, critical alert, malformed, wrong type, unknown MRN, role).
S4 companion endpoints+types+seed (+tests: support content, explainer offline fallback+label,
   forged-id immunity inherited).
S5 calculators +9 (+worked examples). S6 print bounce + web round (self). S7 council (interop
lens) + red-team; gates; wiki; ship v1.4.0.
