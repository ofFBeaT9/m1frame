# Dev evidence — NEXUS v1.2 (pre-red-team snapshot)

- Server: 103/103 vitest green (7 files); tsc strict clean.
- Web: tsc strict clean; vite production build clean (116 modules).
- New server modules: notesService/consentService/triageService/bedService + routes,
  domain/esi.ts, RBAC +2 additive actions, FHIR Consent + DocumentReference in $everything,
  $-sigil rewrite at top-of-router (ordering contract), calculators 13→24.
- Residuals: all six v1.1 items retired with regression tests.
- Council folding (same-cycle): G1 cosign sweep (overdue_cosign alert+audit), G2 draft-blank
  guard, G3 ESI handbook thresholds (+5 assertions), G4 Hillier 2.4 display, E1 writable-types
  gate, E2 consent-templates documentation gate (corrected from council's read_chart suggestion —
  patient role's "own" scope is truthy), E3 FHIR ordering contract, U1–U6 web polish round
  (PatientBanner, ?pid deep links, role-aware landing, admin completeness, handover names,
  record-vitals form).
- Note: council E2's proposed fix (read_chart) would NOT have excluded the patient role —
  contradiction resolved by evidence (test caught it), documentation-privilege gate shipped.
