---
title: NEXUS v1.3 Reach and Trust Cycle
tags: [synthesis, nexus, portal, trust, decision]
related: ["[[NEXUS Clinical Platform]]", "[[NEXUS v1.2 Polish Cycle]]", "[[Honest Scope Labels]]", "[[Residual Retirement]]", "[[Can a Demo Earn Trust]]", "[[m1frame]]"]
created: 2026-06-11
sources: ["nexus-v2-master-prompt"]
page_type: synthesis
confidence: high
---

# NEXUS v1.3 Reach and Trust Cycle

**The verdict:** cycle 3 of the [[NEXUS Clinical Platform]] closed the re-scoped breadth with
[[Honest Scope Labels]] on every demo boundary, and shipped a trust substrate that is real
rather than performative: a WORM hash-chained audit log (tamper-evident by construction,
re-verified on every snapshot restore), HMAC e-signatures at four attestation points with a
public verify endpoint, and durable snapshot persistence. Reach: a patient portal with a
separate lighter identity (released-results-only **with mandatory plain-language clinician
comments**, PHQ-2 with crisis signposting, a "who accessed my record" log with Code Blue
disclosure, today's care plan), a communication hub behind one membership function, call-session
lifecycle, an imaging scaffold with signed structured reports, and print document views.
Shipped as v1.3.0 with **128/128 tests**, strict TS and builds clean. Saved question: [[Can a Demo Earn Trust]].

## What the adversarial process caught
- The **patient advocate** lens (4.5/10 pre-fix) reframed the portal: "a raw data printout where
  a frightened patient needs a companion." All five findings folded same-cycle — most notably
  releases now REQUIRE a clinician comment, and a digital mood screener must never answer a
  distressed person with bare JSON.
- The **red-team** caught a forged-urgent-flag path (UI never offered it; the service never
  blocked it) and a stale test count in the README — an honesty-contract violation by the
  cycle's own standard. Both closed with tests.
- **Process honesty:** two council lens agents were killed by a session limit; their checklists
  were executed directly (yielding the load-time chain verification and the tail-truncation
  anchoring) and the failure is recorded in the study, not papered over.

## Open for cycle 4 (re-scoped out loud)
Portal emergency-contact/visiting-info/diagnosis-explainer surfaces; print-route portal
redirect; per-user signing keys; HL7 v2 ingest; Postgres adapter behind the store choke-point.
