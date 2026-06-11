# Council Paper 4 — Red-Team / QA Attack (gate: CONCERNS → resolved)

Independently ran all four verification commands (103/103 tests, both tsc strict clean, vite
build clean, 116 modules). Verified claims 1, 2, 5; claims 3 and 4 OVERCLAIMED:

- MF-1: the consent-templates "documentation gate" (write_soap||write_vitals) still admitted
  med_tech via write_vitals, contradicting the stated intent — and the gap was untested.
  FIXED: gate tightened to write_soap only (nurses witness consents but don't complete
  templates); web Consent page condition matched; test now asserts patient AND med_tech AND
  nurse get 403, physician 200.
- MF-2: README claimed "97 tests" in two places vs actual 103 (stale after council-fix tests).
  FIXED: both occurrences now 103.

Also verified in passing: cosignOverdueSweep + idempotent test; ESI handbook thresholds with
per-threshold assertions; FHIR ordering contract at top of router; PatientBanner on 5 pages
with graceful null for chart-less roles; HomeRedirect sensible for all roles; RecordVitalsForm
fields match the server; full web-fetch-vs-server-route audit found zero orphans.

Post-fix state: 103/103 tests, tsc clean both sides, build clean.
