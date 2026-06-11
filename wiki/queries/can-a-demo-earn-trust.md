---
title: Can a Demo Earn Trust
tags: [query, nexus, trust]
related: ["[[NEXUS v1.3 Reach and Trust Cycle]]", "[[Honest Scope Labels]]", "[[NEXUS Clinical Platform]]"]
created: 2026-06-11
sources: ["nexus-v2-master-prompt"]
page_type: query
confidence: high
---

# Can a Demo Earn Trust

**Saved question:** can a demo-grade system make legitimate trust claims (durability,
tamper-evidence, signatures) without a production substrate — or is "demo trust" theatre?

**Answer:** yes, iff every mechanism is real-but-bounded and the bound is stated as loudly as
the feature ([[Honest Scope Labels]]). Proven in [[NEXUS v1.3 Reach and Trust Cycle]] on the
[[NEXUS Clinical Platform]]: a hash chain that genuinely detects edits (and says plainly it
cannot see tail truncation, returning the anchor data that can), HMAC signatures that genuinely
bind content (and say plainly they are not non-repudiation), snapshots that genuinely survive
restarts (and state the 10s crash window). The red-team verified the labels against the code as
claims — and the one stale claim it found (a test count) was treated as a must-fix, because an
inaccurate honesty label spends credibility earned everywhere else. 128/128 tests.
