---
title: Residual Retirement
tags: [concept, quality, process, release-discipline]
related: ["[[Clinical Safety Loops]]", "[[NEXUS v1.2 Polish Cycle]]", "[[NEXUS Clinical Platform]]"]
created: 2026-06-11
sources: ["nexus-v2-master-prompt"]
page_type: concept
confidence: high
---

# Residual Retirement

A release-discipline rule: **a codebase is "spotless" only when every documented known-gap is
either fixed with a regression test or explicitly re-scoped — documenting a defect is a liability
ledger entry, not a resolution.** Honest READMEs that list residuals (as the
[[NEXUS Clinical Platform]] did after its v1.1 cycle) are far better than silence, but each entry
accrues interest: reviewers re-find it, users hit it, and the next cycle pays compound cost.

Practice, as executed in [[NEXUS v1.2 Polish Cycle]]:
1. Open the cycle by enumerating the residual ledger (six items in v1.2's case).
2. Retire each with a code fix AND a regression test that would fail on the previous release —
   the test is what converts "we said we fixed it" into evidence.
3. Anything not retired must be re-scoped out loud (moved to the next-cycle list with a reason),
   never silently carried.

Complement to [[Clinical Safety Loops]]: loops decide *what to build first*; residual retirement
decides *when you may call it done*.
