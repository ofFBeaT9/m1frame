---
title: m1frame Studio
tags: [ui, studio, real-time, sse, deliberation, hermes]
related: ["[[m1frame]]", "[[MVP Architecture Decision]]", "[[m1frame Constellation Release]]"]
created: 2026-06-03
sources: ["m1frame-studio"]
page_type: synthesis
confidence: high
---

# m1frame Studio

The **real-time UI** for [[m1frame]] — a zero-build, offline, single-file web app that turns the batch pipeline
into a watchable **deliberation theatre**. Type a goal and see all seven pillars work live: BMAD stories appear,
the Council debates persona-by-persona with an **independent red-team that can veto a pass**, the knowledge graph
grows node-by-node, and the miras memory feed pulses.

## What it is
Seven surfaces over one event stream (`agents/events.py` → Server-Sent Events): **Studio** (live deliberation),
**Chat** (grounded, cited), **Graph** (the knowledge constellation), **Runs** (replayable event traces),
**Skills** (council-vetted learned recipes), **Wiki** (this graph), **Settings** (one-click backend switch,
tools, gateways, scheduler, metrics). Three tiers so it always runs: live (FastAPI + key), server-replay (no
key), pure-static (no pip). Hand-built CSS, no CDN — a "deep observatory" aesthetic.

## Why it matters (the honest positioning)
Benchmarked against **Hermes Agent**, m1frame does **not** out-feature it on tool breadth or maturity. It leads
decisively on **one axis — transparency you can trust**: visible multi-agent deliberation, a red-team that
overrides an overconfident pass (real in `agents/council.py`, not just the UI), click-through grounding in a live
knowledge graph, and visible memory. The honest headline: *"the most auditable multi-agent workspace there is."*

## Proof
The bundled demo replays a full [[MVP Architecture Decision]] deliberation — the council debate, the red-team's
"microservices don't remove coupling" correction, and the final verdict — with zero API key. The framework's own
gateways, tool surface, and persistent runs are described in the [[m1frame Constellation Release]].
