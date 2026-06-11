---
title: Honest Scope Labels
tags: [concept, trust, demo-engineering, process]
related: ["[[Residual Retirement]]", "[[NEXUS v1.3 Reach and Trust Cycle]]", "[[NEXUS Clinical Platform]]"]
created: 2026-06-11
sources: ["nexus-v2-master-prompt"]
page_type: concept
confidence: high
---

# Honest Scope Labels

A demo earns trust by **stating precisely what each capability is NOT**, in the same breath as
what it is. The pattern, generalized from the [[NEXUS Clinical Platform]]'s AI degraded mode
("AI Offline, never fake an answer") and made systematic in [[NEXUS v1.3 Reach and Trust Cycle]]:

| Shape of the label | Example |
|---|---|
| Real mechanism, bounded guarantee | Hash-chained audit: tamper-EVIDENT, not tamper-proof; cannot see tail truncation alone — anchor `{length, head_hash}` off-host |
| Real workflow, simulated transport | Video calls: full waiting-room lifecycle, audited — no media transport |
| Real data, simulated rendering | Imaging: signed structured reports — no DICOM pixels |
| Real attestation, custodial key | HMAC e-signatures: integrity + attribution — not legal non-repudiation |

Rules: (1) the label lives next to the feature (README table + code comments + UI captions),
never in a separate disclaimer page; (2) the verifier endpoint exposes the limitation's
mitigation (the audit verifier returns the anchoring hint); (3) a red-team checks the labels
against the code as claims — an inaccurate honesty label is the worst defect class, because it
spends credibility earned elsewhere. Companion to [[Residual Retirement]]: retirement governs
*when you may ship*, labels govern *what you may say*.
