---
title: NEXUS Clinical Platform
tags: [clinical, full-stack, news2, rbac, fhir, code-blue, build, synthesis]
related: ["[[NEXUS Build Prompt v2.0]]", "[[m1frame]]", "[[m1frame Constellation Release]]"]
created: 2026-06-10
sources: ["nexus-build-prompt-v2"]
page_type: synthesis
confidence: high
---

# NEXUS Clinical Platform

A runnable, tested implementation of [[NEXUS Build Prompt v2.0]], produced by **two full
[[m1frame]] 7-pillar cycles**. It lives at `nexus/` (server + web). This page is the institutional
memory of *how* the build was scoped and *what* the council learned.

## The load-bearing decision: build the safety spine, scaffold the breadth
The spec has 21 sections; a single session cannot ship all of them at production depth without
faking it. QA Gate 1 ruled: a **correct, tested safety spine** beats a broad-but-shallow clone.
The spine = age-adjusted vitals → **NEWS2/qSOFA** → alerts → **audit** → **three-layer RBAC** →
**Code Blue override** → **FHIR R4 export**. Everything else is scaffolded with typed seams, and the
externals (WebRTC/coturn, OHIF/DICOM, hosted Supabase, live Anthropic) are labelled out-of-scope —
never faked as done.

## Why it runs offline (and still ports to Supabase)
The in-memory data layer mirrors the spec §17 columns exactly, and **one `authorize()` choke-point**
is the "RLS" layer. Swapping to Supabase is a single interface reimplementation. The AI engine
defaults to the spec-mandated **degraded mode** — with no API key it returns a structured "AI Offline"
result and never throws, so the app is provably never blocked by AI.

## What the two cycles changed (fix, don't caveat)
- **Cycle 1** built the spine + breadth scaffold; an independent **red-team scored it 6.5/10**,
  finding a sex-blind CHA₂DS₂-VASc recommendation, a *duplicated* unvalidated NEWS2 that dropped the
  single-red escalation band, an unguarded monitoring-board route, and an under-audited Code Blue
  extend/end.
- **Cycle 2** folded **every** critical/high/medium finding into code with regression tests:
  calculators now delegate to the single validated `news2()`/`qsofa()`; the board routes through the
  same `authorize()` gate; CHA₂DS₂-VASc no longer over-treats a sex-only point; Code Blue
  extend/end are audited and capped. Re-gate: **PASS**.

## Proven state
41 server tests green (NEWS2/qSOFA vs RCP/Sepsis-3 worked examples, three-layer RBAC, Code Blue
403→activate→200 flow, FHIR Bundle, calculators, AI degraded mode); strict typecheck clean; web
production build green; app boots and serves the monitoring board (ICU-01 septic shock → NEWS2 18
dark-red), FHIR export, and the Code Blue flow end-to-end.

## Reusable lesson
This is the same pattern [[m1frame Constellation Release]] used: **one independent red-team beats ten
agreeable agents**, and a tested narrow spine is worth more than an untested broad surface. The
"fix-don't-caveat" rule turned a 6.5 Cycle-1 build into a gated 8.4 deliverable.
