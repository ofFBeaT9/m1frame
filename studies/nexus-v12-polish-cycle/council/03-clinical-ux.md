# Council Paper 3 — Clinical UX / Product Completeness (score 6.5/10, mid-cycle snapshot)

Reviewed while the web build agent was still in flight, so its central finding — "the four v1.2
pages don't exist" — was resolved by that agent within the hour (Notes/Consent/Triage/Beds all
shipped, tsc + build green). Durable findings, ranked and folded:

U1 PatientConsole had no links into Orders/MAR/Labs/Notes/Consents (silo navigation, re-select
   patient each time) → quick-link strip + ?pid= deep links.
U2 med_tech landed on Monitoring and got an endless "Loading ward…" on a silent 403 → role-aware
   landing redirect + explicit 403 message on the board.
U3 Patient-scoped pages lacked a patient banner (wrong-patient risk) → PatientBanner component
   (name · MRN · bed · allergy chips) on Orders/MAR/Labs/Notes/Consent.
U4 Admin silently dropped fetched stats (encounters, calculator_uses) and had zero visibility of
   triage/beds/co-sign queues → tiles + summary cards added.
U5 Handover rendered raw user ids; Admin audit timestamps were time-only → formatted.
U6 POST /patients/:id/vitals was unreachable from the UI (nurse demo dead-end) → Record-vitals
   form on the console.

Honesty check: README claims matched the server but preceded the web pages (resolved by delivery
order, not wording). Patient-role experience remains a clinician console scoped to one card —
README's "own record only" stands, full portal (§14) stays the top next-cycle item.
