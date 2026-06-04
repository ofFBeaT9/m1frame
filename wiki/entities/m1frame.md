---
title: m1frame
tags: [framework, multi-agent, bmad, council, miras, wiki]
related: ["[[m1frame Studio]]", "[[Chip Manufacturing Decision]]", "[[Tritone]]"]
created: 2026-06-03
sources: ["m1frame-studio"]
page_type: entity
confidence: high
---

# m1frame

A **portable, offline-capable multi-agent framework** that doesn't just *act* — it **deliberates, grounds, and
remembers**. Seven pillars run as one pipeline: BMAD (story backlog) → Council brainstorm → OpenPlanter
(investigation) → Miras (multi-agent execution) → Karpathy (`<thought>` refinement) → Council review (a QA gate
with an **independent red-team**) → LLM-wiki (this knowledge graph). Memory is held in miras; LLM backends switch
in one line (Claude / OpenAI / Ollama / vLLM / LM Studio). Zero lock-in, git-versionable.

This is the engine that produced the [[Chip Manufacturing Decision]] for [[Tritone]] — a 3-member council plus a
red-team, grounded in this very wiki. [[m1frame Studio]] is the real-time UI that makes that deliberation
visible, watchable, and replayable.
