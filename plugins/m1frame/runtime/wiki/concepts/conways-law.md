---
title: Conway's Law
tags: [architecture, organization, concept, demo]
related: ["[[MVP Architecture Decision]]", "[[Microservices]]"]
created: 2026-06-04
sources: ["mvp-architecture-demo"]
page_type: concept
confidence: high
---

# Conway's Law

> "Organizations design systems that mirror their own communication structure."

Practical corollary for the [[MVP Architecture Decision]]: your service boundaries will end up matching your team
boundaries, so **don't create more services than you have teams to own them**. A small pre-PMF team is one team —
which argues for one deployable ([[Modular Monolith]]) rather than a fleet of [[Microservices]] no one can staff
on-call.
