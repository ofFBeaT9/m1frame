# Council Paper 2 — Engineering Quality (score 7/10, pre-fix)

(a) Notes routes: 404-cloak discipline correct on all note-id mutations; patient-path writes
authorize correctly. **E1** — GET /notes/writable-types had no permission gate (structure
disclosure). **E2** — GET /consent/templates requireAuth-only (template internals readable by
patient/med_tech). Triage/beds permission-level gating judged CORRECT by domain (null patient_id
records; unit infrastructure). (b) **E3** — FHIR $-sigil rewrite middleware was registered after
/r4/:resource/:id — accidentally correct, fragile ordering. %24 handling correct, no
double-decode. (c) Single-writer rule verified: bedService is the only live writer of
Encounter.bed_id; seed's direct construction is bootstrapping in the correct direction.
(d) Tests behaviour-oriented; gaps named: triage progress invalid-state/role, consent templates
access, non-author draft edit, FHIR cross-patient purity. (e) Debts = E3 + E1/E2.

DISPOSITION (folded in-cycle): E1 → documentation-privilege gate. E2 → documentation-privilege
gate (NB: read_chart would NOT exclude the patient role — its "own" scope is truthy; council's
suggested fix was corrected during implementation). E3 → rewrite + $everything route moved to the
top of the router with an ORDERING CONTRACT comment. All four named test gaps now have tests,
including the $everything cross-patient purity check.
