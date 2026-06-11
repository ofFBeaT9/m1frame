# Council Paper 1 — Patient Advocate & Health Literacy (score 4.5/10, pre-fix)

Walked Ahmad Karimi's journey end-to-end. Verdict: "security scaffolding sound, but the portal
delivers clinical metadata to a frightened patient with almost no interpretive context."

Findings → dispositions (ALL folded in-cycle):
- P1 lab release had no clinician comment → release now REQUIRES a 10-280 char plain-language
  release_comment, surfaced with the results (+ tests).
- P2 PHQ-2 left a distressed patient with bare JSON; max score was severity "info" → every
  response carries a support_message (crisis signposting incl. 988 at near-max), score ≥5
  escalates to "warning" (+ tests).
- P3 no access transparency → GET /portal/access-log: who/when/what touched my record, with
  Code Blue override disclosure (HIPAA Right of Access / Cures Act) (+ tests).
- P4 patient cannot see the plan → GET /portal/plan serves the latest finalized note's plan
  section as "What your team is doing today" (+ test).
- P5 patient user absent from their own channel's member_ids (link-table access masked it) →
  seed adds linked patient users to membership (+ test).
- Health literacy: portal analytes now carry display_name ("Creatinine (kidney function
  marker)") and gentle patient_status strings instead of raw CRITICAL_* flags (+ tests).
Deferred to next cycle (re-scoped out loud): emergency contact surface, visiting info,
plain-language diagnosis explainer (AI education endpoint exists but is not yet portal-wired).
