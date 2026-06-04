---
title: MVP Architecture Decision
tags: [architecture, monolith, microservices, decision, demo]
related: ["[[Modular Monolith]]", "[[Microservices]]", "[[Conway's Law]]", "[[Premature Decomposition]]", "[[m1frame]]"]
created: 2026-06-04
sources: ["mvp-architecture-demo"]
page_type: synthesis
confidence: high
---

# MVP Architecture Decision

**The answer:** ship a **[[Modular Monolith]]**, extraction-ready — *not* **[[Microservices]]**, not yet. This is
the bundled m1frame demo: a 3-member council plus a red-team deliberating a decision every software team faces.

## The verdict
1. **One deployable, many bounded contexts.** Model each domain as an in-process module behind a narrow
   interface — one database, trivial CI. Simplicity is a feature.
2. **Strict seams.** Because modules talk through interfaces, any one can later be lifted into a standalone
   service **without a rewrite**.
3. **Gate the split on real triggers:** sustained load a single box can't serve, a team large enough to own a
   service end-to-end, or a genuine need for independent deploys.
4. **Why now:** before product-market fit there is ~no scaling pressure, and distributed systems carry constant
   ops cost — microservices **relocate** coupling to the network rather than removing it.

## How the council got here
Three independent lenses — product (ship speed), operations ([[Premature Decomposition]] is expensive), and
architecture ([[Conway's Law]]: one service per team you actually have) — converged. The lone "microservices
remove coupling" dissent was **self-disqualified by the red-team**, which noted coupling merely moves to the
network (partial failure, retries, versioned contracts). Consensus **8.0/10**.
