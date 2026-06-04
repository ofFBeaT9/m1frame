---
title: m1frame
tags: [framework, multi-agent, bmad, council, miras, wiki]
related: ["[[m1frame Studio]]", "[[MVP Architecture Decision]]", "[[m1frame Constellation Release]]"]
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
in one line (Claude / OpenAI / OpenRouter / Ollama / vLLM / LM Studio and more). Zero lock-in, git-versionable.

The bundled demo runs this pipeline on a generic, relatable decision — the [[MVP Architecture Decision]]
(monolith vs microservices) — so a new user can watch a 3-member council plus a red-team deliberate, ground, and
remember, with no API key. [[m1frame Studio]] is the real-time UI that makes that deliberation visible,
watchable, and replayable.
