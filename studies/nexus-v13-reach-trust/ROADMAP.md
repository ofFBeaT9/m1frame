# ROADMAP — NEXUS v1.3 "Reach & Trust"

## 1. Analyst — Project Brief
**Problem.** v1.2 serves clinicians well; the patient persona sees a clinician console, documents
cannot leave the system (no print), nothing survives a restart, and the audit log — the legal
spine — is append-only by convention, not by construction. Cycle 3 = reach (portal, chat, print,
imaging) + trust (durability, tamper-evidence, signatures).
**Anchors.** Patient channel scoping rules already exist in the RBAC matrix (chat: "own-team");
release_results permission exists with no flow; upload_imaging exists with no module; store
choke-point makes persistence a swap-in; audit() is a single function — one place to add a hash
chain; node:crypto suffices for HMAC + SHA-256 (zero new deps).
**Hypothesis.** All five tracks land in one cycle BECAUSE each reuses an existing seam, and the
trust items are small once located at the right choke-points (audit(), finalize/record/administer).

## 2. PM — PRD
**Goal.** v1.3.0: every persona has a real surface; documents print; records survive restarts;
the audit chain is tamper-evident; clinical attestations carry verifiable signatures. Honest
labels on every demo boundary.
**FRs.**
- FR1 Trust/persistence: JSON snapshot of the whole store to `server/data/nexus-db.json` —
  periodic (10s) + on SIGINT/SIGTERM; load-on-boot when present; `ENABLE_PERSISTENCE` env
  (default on for dev, OFF under tests for determinism); reseed only when no snapshot.
- FR2 Trust/WORM: every AuditEntry gains `seq`, `prev_hash`, `entry_hash` (SHA-256 over canonical
  entry + prev hash). `verifyAuditChain()` detects any historical mutation; admin endpoint
  `GET /admin/audit/verify`; regression test mutates a row and proves detection.
- FR3 Trust/e-signatures: HMAC-SHA256 (SIGNING_SECRET) over canonical content at three
  attestation points — note finalize, consent record, MAR administration. `signature` stored;
  `GET /verify/:type/:id` re-derives and reports valid/invalid; tamper test included. Honesty:
  server-key custody = integrity + attribution, not legal non-repudiation.
- FR4 Imaging scaffold (§3.7): ImagingStudy records (modality, sub-type, study_uid, simulated
  upload), structured radiology report (indication/technique/findings/impression) signed on
  reporting; statuses ordered→performed→reported; FHIR ImagingStudy + RAD DiagnosticReport in
  $everything; web Imaging page.
- FR5 Communication hub (§13): channels (patient/department/dm/broadcast) with membership rules —
  patient channel = care team + linked patient user; department = unit staff + admin; messages
  with urgent flag + per-user read receipts (read marked on fetch); DM create-or-get; broadcast
  admin-only post. Call sessions: initiate (patient → waiting room), admit, end — logged +
  audited, NO media transport (honest label). Web Chat page with 5s polling.
- FR6 Print/export (§12): print-optimized document views (light palette, @media print) for
  discharge summary (new server assembly endpoint), lab report, consent document, MAR record;
  Print buttons on owning pages; browser print (honest label: no server-side PDF).
- FR7 Patient portal (§14): separate lighter visual identity under /portal; Overview (admission,
  care team, bed), Results (RELEASED panels only — release flow added for release_results
  holders on the Labs page), Medications (active orders, patient-friendly), Consents, Messages
  (patient's own care-team channel), PHQ-2 questionnaire (stored; score ≥3 raises an info alert
  to the care team). Patient HomeRedirect → /portal.
**NFRs.** No new runtime deps; strict TS; all 103 v1.2 tests keep passing (persistence OFF in
test env); ≥125 total tests; honest README labels per boundary.
**Out of scope.** Live WebRTC media, server PDF rendering, DICOM parsing/rendering, per-user
key pairs / qualified signatures, Postgres (snapshot persistence is the documented bridge),
appointments scheduling beyond a seeded read-only list.

## 3. Architect — design (falsifiable)
- NEW `db/persistence.ts`: serialize(db)+patientUserLinks → JSON; `load()` restores arrays
  in-place (keeps references); `start()` interval + signal hooks; config.persistence flag
  (default !NODE_ENV=test). index.ts calls load-or-seed.
- `store.audit()` extended: seq = audit_log.length, prev_hash = last.entry_hash ?? GENESIS,
  entry_hash = sha256(canonical(entry_without_hash)+prev_hash). NEW `domain/worm.ts` with
  canonicalize + verifyAuditChain. Admin route + tamper test.
- NEW `domain/signatures.ts`: hmacSign(kind, id, canonicalContent), verify(kind, id, content,
  signature). Wire: notesService.finalizeNote, consentService.recordConsent,
  marService.administerDose → store `signature`. NEW route `GET /verify/:kind/:id` (read_chart +
  authz on the underlying patient).
- types += ImagingStudy, Channel, ChatMessage, CallSession, Appointment, QuestionnaireResponse;
  store += tables + helpers (channelsFor(user), unreadCount, releasedLabs(patientId)).
- LabPanel += released_to_patient_at/by; labs route POST /labs/:id/release (release_results).
- NEW services: imagingService, chatService (membership rules = the security core), callService,
  portalService (own-record assembly, PHQ-2 scoring per Kroenke 2003: ≥3 positive screen).
- NEW routes: imaging.ts, chat.ts (includes calls), portal.ts (every endpoint hard-scoped to the
  LINKED patient — never trusts a patient id from the request), print data via existing APIs +
  one GET /patients/:id/discharge-summary assembly.
- Web: Portal layout wrapper with light palette (`portal-light` class scope), pages
  PortalHome/Results/Meds/Consents/Messages/Questionnaire; Chat page; Imaging page; 4 print
  views + buttons; Labs gains Release button; HomeRedirect patient→/portal.
**Falsifiable:** (a) zero new npm deps; (b) all 103 v1.2 tests pass unmodified (persistence off
under vitest); (c) chain verification flags a single-byte historical edit; (d) portal endpoints
return 403/404 for any non-linked patient data even with a forged id in the body.

## 4. Scrum Master — Epic & stories
EPIC: NEXUS v1.3 "Reach & Trust".
- S1 WORM hash-chain + verify endpoint + tamper test.
- S2 E-signatures at 3 attestation points + verify route + tamper test.
- S3 Persistence (snapshot/load/start, env-gated) + round-trip test (explicit save/load, no timers).
- S4 Imaging module + FHIR + tests (role gates, report lock + signature).
- S5 Chat channels/messages/read-receipts/urgent + membership tests (patient own-team only;
  nurse no cross-unit dept channel). Calls: waiting→admit→end + audit + tests.
- S6 Results release flow + portal endpoints (own-scope hard-coded) + PHQ-2 + tests.
- S7 Discharge-summary assembly endpoint + seed expansion (channels, imaging, appointments,
  released lab, PHQ-2 sample) + version 1.3.0 + README honesty table.
- S8 Web (delegated agent): Portal suite + Chat + Imaging + print views + Release button +
  HomeRedirect. tsc + build must pass.
- S9 Council (patient-advocate lens, security/trust lens, engineering lens) + red-team; fold;
  gates; wiki; report; ship.
Dependencies: S1-S3 independent; S4-S6 parallel after types; S7 after S4-S6; S8 after routes;
S9 last.
