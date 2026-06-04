---
title: Microservices
tags: [architecture, microservices, distributed, demo]
related: ["[[MVP Architecture Decision]]", "[[Modular Monolith]]", "[[Conway's Law]]"]
created: 2026-06-04
sources: ["mvp-architecture-demo"]
page_type: entity
confidence: high
---

# Microservices

An architecture that splits a system into independently deployable services communicating over the network. It
genuinely helps at scale — independent deploys, per-service scaling, team autonomy — once you have the **load and
the headcount** to justify it (see [[Conway's Law]]).

The trap the council's red-team flags: microservices do **not** eliminate coupling, they **relocate** it to the
network, adding partial failure, retries, idempotency, distributed tracing, and versioned contracts. Before
product-market fit those costs usually outweigh the benefit — hence the [[Modular Monolith]] wins the
[[MVP Architecture Decision]] until a real trigger fires.
