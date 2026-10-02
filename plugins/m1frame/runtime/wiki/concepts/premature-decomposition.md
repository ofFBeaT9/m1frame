---
title: Premature Decomposition
tags: [architecture, anti-pattern, concept, demo]
related: ["[[MVP Architecture Decision]]", "[[Modular Monolith]]"]
created: 2026-06-04
sources: ["mvp-architecture-demo"]
page_type: concept
confidence: high
---

# Premature Decomposition

Splitting a system into services **before** the load, team size, or domain boundaries are understood — paying the
full distributed-systems cost up front to buy scalability you don't yet need. Its common failure mode is the
**"distributed monolith"**: services so chatty they must deploy together — all the cost of distribution, none of
the independence.

It is the central anti-pattern the [[MVP Architecture Decision]] avoids by starting from a [[Modular Monolith]]
and extracting services only on a real trigger.
