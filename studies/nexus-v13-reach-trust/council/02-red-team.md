# Council Paper 2 — Red-Team / QA Attack (gate: CONCERNS → resolved)

Ran all four verification commands independently (127/127 at attack time; both tsc clean; build
clean, 128 modules). Verified the full trust + reach synthesis claim-by-claim (23 verdicts,
21 VERIFIED), including: persistence chain re-verification + corrupted-file refusal,
release_comment enforcement server AND web, PHQ-2 escalation + signposting, access-log patient
isolation (incl. null-row and cross-patient probes), patient channel membership, App-level
patient segregation, web-fetch-vs-server-route audit (zero orphans), wrong-kind verify handling,
seed comment length compliance.

MUST-FIXES (both closed in-cycle):
- MF-1: README still said 124 tests (actual 127, then 128 after MF-2's test) — fixed to 128.
- MF-2: a patient could forge is_urgent=true via raw API (UI never offered it, service never
  blocked it) — postMessage now 403s patient-set urgent flags with a kind explanation; test added.
Accepted with label: print routes show patients a dead "no access" div instead of a portal
redirect (no data served — server-gated); cosmetic, queued.
