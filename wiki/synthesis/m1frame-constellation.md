---
title: m1frame Constellation Release
tags: [release, gateways, tools, mcp, deploy, hermes, readiness]
related: ["[[m1frame]]", "[[m1frame Studio]]", "[[Is m1frame v1.3 Production Ready]]"]
created: 2026-06-04
sources: ["m1frame-v1.3-readiness"]
page_type: synthesis
confidence: high
---

# m1frame Constellation Release

**v1.3 "Constellation"** is the release where [[m1frame]] stopped being "a great dashboard with a thin agent"
and became a credible agent that still leads on auditability. It closes — *in code, tested* — the architecture
gaps that were real against **Hermes Agent** in v1.2.

## What shipped (commit `3c3b6f9`)
- **Messaging gateways** (`gateways/`): one transport-agnostic `GatewayRouter` (commands · `/run` deliberation ·
  grounded chat) behind **Telegram / Slack / Discord / webhook / CLI** adapters. API `POST /gateway/{platform}/webhook`
  (SSRF-guarded), `GET /gateway/status`. Run locally via `python -m gateways`.
- **Agent tool surface** (`tools/`): a `ToolRegistry` + auditable built-ins (AST-safe calculator, wiki_search,
  datetime, word_count, SSRF-guarded http_get) + an **MCP client** connector. API `GET /tools`, `POST /tools/call`.
- **Persistent run store**: runs written atomically to `runs/<id>.json`, reloaded on startup, searchable via
  `GET /runs/search` — history survives restarts and stays replayable in [[m1frame Studio]].
- **More providers** (nous / novita / nvidia_nim → 9 backends) and **Docker** (`docker compose up`).

## The honest verdict
Readiness audit (this pipeline): **GO for its positioning** — *the most auditable multi-agent workspace* — at
council consensus **8.3/10**, **90/90** offline QA, 0 wiki lint errors. It is **not** "superior to Hermes
overall": Hermes still leads on tool **breadth** (40+ vs 5), gateway **platform count**, deploy **targets**, and
~10k-commit **maturity**. Those are breadth-and-time gaps, not architecture gaps. See
[[Is m1frame v1.3 Production Ready]] and `studies/m1frame-v1.3-readiness/`.

## The #1 remaining gap
**Tool breadth + live-validated channels** — deepen the `tools/` set and exercise the gateway adapters against
real Telegram/Slack credentials. Highest leverage because it converts "architecture present" into "surface area
proven," which is the last thing standing between m1frame and a head-to-head with Hermes on its own turf.
