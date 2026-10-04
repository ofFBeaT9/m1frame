---
title: m1frame Optional Modules
tags: [synthesis, integration, actionability, compression]
related: ["[[m1frame]]", "[[ADHD-Friendly Output]]", "[[Headroom Context Compression]]"]
created: 2026-09-15
sources: ["i-have-adhd", "headroom"]
page_type: synthesis
confidence: high
---

# m1frame Optional Modules

The two upstream projects solve different problems and should not be merged into
one opaque layer. [[ADHD-Friendly Output]] changes only final prose and prompt
guidance; [[Headroom Context Compression]] changes provider messages only when
explicitly enabled. Keeping both optional preserves m1frame's offline,
dependency-light baseline while exposing a measurable path for better
actionability and smaller contexts.

Operational configuration guidance is saved in [[Should Optional Modules Be Enabled]].
