---
title: Modular Monolith
tags: [architecture, monolith, demo]
related: ["[[MVP Architecture Decision]]", "[[Microservices]]"]
created: 2026-06-04
sources: ["mvp-architecture-demo"]
page_type: entity
confidence: high
---

# Modular Monolith

A single deployable application internally organized into **bounded-context modules** that communicate through
narrow, explicit interfaces — one process, one database, trivial CI. It captures most of the design discipline of
**[[Microservices]]** (clear ownership, separable domains) with none of the distributed-systems tax.

Its decisive property for an MVP: because module boundaries are strict, any module can be **extracted into a
standalone service later without a rewrite** — so it is the low-regret default in the [[MVP Architecture Decision]].
