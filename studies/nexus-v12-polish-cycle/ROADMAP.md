# ROADMAP — NEXUS v1.2 "Clinical Record & Professional Polish"

## 1. Analyst — Project Brief
**Problem.** v1.1 closed the safety loops but the platform still lacks the *clinical record
spine* (notes with a legal amendment trail, consent) and the *patient-flow surface* (triage,
beds), and carries six documented residuals. "Spotless" means: zero known-but-unfixed defects,
professional surfaces, every claim test-backed.
**Anchors (from cycle-1 evidence, not assumption):** write_soap exists in the RBAC matrix with no
implementation; Encounter has triage_score/triage_system/bed_id unused; units carry bed_count but
no bed inventory; medico-legal paper named consent + amendment trail the #1 exposure; red-team
noted the FHIR $-sigil gap.
**Hypothesis.** One cycle can ship notes+consent+triage+beds because all four reuse the proven
seams (store choke-point, audit-everything, single matrix, lazy patterns), and "spotless" is
achievable by retiring every residual WITH a regression test rather than re-documenting it.

## 2. PM — PRD
**Goal.** v1.2.0: the clinical record becomes legally-shaped (immutable finalized notes,
addenda, co-sign dashboard, consent with witness), patient flow becomes visible (ESI triage
queue, live bed board), all six residuals retired, calculator suite roughly doubled, web
surfaces professional.
**FRs.**
- FR1 Notes: draft→finalize lifecycle; finalized notes LOCKED (any edit attempt rejected);
  amendments are append-only addenda (original preserved verbatim, author+timestamp+reason);
  resident-authored notes require attending co-signature; pending-cosign feed; note types
  soap/progress/nursing/procedure/consult; nursing notes writable by write_vitals holders,
  clinical notes by write_soap holders.
- FR2 Consent: seeded template library (surgical, transfusion, procedure, anaesthesia, AI
  analysis, video recording); physician completes fields; patient signature (typed, demo-grade)
  + witness signature where template requires; witness ≠ signing physician; consents linked to
  the patient record and exported as FHIR Consent.
- FR3 Triage: ESI 1–5 assessment with decision-tree auto-suggestion (vitals + presentation
  flags); nurse confirms or overrides WITH reason; ESI-1 raises a critical alert to charge/
  physician; waiting-room board sorted severity→arrival; admit action stamps Encounter
  triage_score/triage_system.
- FR4 Beds: per-unit bed inventory (ICU 8, GM 16, Paeds 12) seeded with live statuses;
  assign/transfer/release workflow (occupied→cleaning→available), transfer reason mandatory,
  Encounter.bed_id kept in sync, all transitions audited; board endpoint per unit.
- FR5 Residuals retired (each with a test): FHIR `$everything` sigil alias; NEWS2 medium band
  (5–6) raises a warning alert; K⁺ critical_high 6.5→6.0; controlled-substance witness
  CO-AUTHENTICATES (supplies own password — substance, not form); paracetamol projected daily
  dose >4 g/day (adult) soft stop; metformin at eGFR<30 hard stop.
- FR6 Calculators: +11 cited, deterministic: CURB-65, Wells DVT, HEART, HAS-BLED, MELD-Na,
  Child-Pugh, APGAR, Centor/McIsaac, FeNa, Serum Osmolality, Corrected Na (hyperglycaemia).
- FR7 Web: Notes (in-console workflow incl. amend + co-sign), Consent, Triage board, Beds board;
  professional polish on all surfaces; README updated honestly; versions → 1.2.0.
**NFRs.** No new server runtime deps; strict TS both sides; all v1.1 tests keep passing (except
where a residual fix deliberately changes asserted behaviour — those assertions update with the
fix); ≥95 total tests.
**Out of scope.** Patient portal UI, chat/video, imaging/DICOM, print/PDF, Supabase/WORM,
real signature capture, HL7 v2 ingest.

## 3. Architect — Technical design (falsifiable)
- types.ts += ClinicalNote {sections, status draft|final, amendments: Amendment[], cosign_*},
  ConsentTemplate, ConsentRecord, TriageRecord {esi_suggested, esi_final, override_reason,
  status waiting|in_treatment|admitted|discharged}, Bed {status, current_patient_id}.
- store.ts += notes, consent_templates, consents, triage_queue, beds + helpers
  (pendingCosign(uid), bedsForUnit, waitingTriage). Choke-point untouched.
- NEW domain/esi.ts: pure suggestEsi(input) decision logic (RR/SpO2/SBP/LOC/arrest flags → 1;
  high-risk presentation or qSOFA-like → 2; resources est → 3/4/5). Cited to ESI v4 handbook.
- NEW services/{notesService, consentService, triageService, bedService}.ts — all mutations
  audit(); finalized-note immutability enforced in service (route cannot bypass).
- domain/medSafety.ts: paracetamol daily projection (dose × freq multiplier), metformin renal
  hard stop; marService: witness_password verification; labRanges: K 6.0; vitalsService: medium
  band warning alert; routes/fhir.ts: literal "$everything" alias route (Express 4 treats $ as
  literal) + Consent/DocumentReference in the Bundle.
- RBAC: two additive actions — "triage" (admin, physician, resident, np_pa, nurse) and
  "bed_management" (admin, physician, nurse). Client matrix ships automatically via /auth/me.
- Routes: notes.ts, consent.ts, triage.ts, beds.ts under /api; resource-id mutations use
  lookup-then-authorize with 404 cloak (cycle-1 lesson).
- Calculators: extend CALCULATORS array; each with citation + interpretation bands; worked-
  example unit tests (e.g. CURB-65=3 → inpatient; MELD-Na vs published example).
**Falsifiable:** (a) all four features land without modifying authorizePatientAccess or the
middleware; (b) v1.1 test files unchanged except MAR witness co-auth + K+ threshold assertions;
(c) every FR5 residual has a test that FAILS on v1.1 code.

## 4. Scrum Master — Epic & stories
EPIC: NEXUS v1.2 "Clinical Record & Professional Polish".
- S1 Notes engine + tests (lock, addendum immutability, co-sign, role scoping).
- S2 Consent (templates, witness rules, FHIR Consent) + tests.
- S3 Triage (esi.ts pure logic, queue, ESI-1 alert, override reason, admit linkage) + tests.
- S4 Beds (inventory, lifecycle, transfer reasons, encounter sync, board) + tests.
- S5 Residuals (6 fixes, 6 regression tests, update 2 existing assertions).
- S6 Calculators +11 with worked-example tests.
- S7 Seed expansion (notes incl. amended + pending-cosign, consents, triage queue w/ ESI-1,
  bed statuses) + FHIR bundle additions.
- S8 Web: 4 new surfaces + polish + nav/routes (delegated agent; tsc + build must pass).
- S9 Council (3 lenses) + red-team; fold all fixes; QA gate 2; wiki ingest; report; ship 1.2.0.
Dependencies: S1–S6 parallelizable server-side; S7 after S1–S4; S8 after routes stable; S9 last.
