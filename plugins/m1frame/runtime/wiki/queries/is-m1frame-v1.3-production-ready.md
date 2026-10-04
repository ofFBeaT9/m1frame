---
title: Is m1frame v1.3 Production Ready
tags: [query, readiness, hermes, verdict]
related: ["[[m1frame Constellation Release]]", "[[m1frame]]"]
created: 2026-06-04
sources: ["m1frame-v1.3-readiness"]
page_type: query
confidence: high
---

# Is m1frame v1.3 Production Ready

**Q.** Is m1frame v1.3 "Constellation" production-ready, and what is the single highest-priority remaining gap
versus Hermes Agent?

**A. GO — production-ready *for its positioning*** ("the most auditable multi-agent workspace"), at council
consensus **8.3/10** with **90/90** offline QA and 0 wiki-lint errors. The [[m1frame Constellation Release]]
closes the gateway / tool / persistence / deploy *architecture* gaps in tested code, and every new subsystem is
best-effort — it can never break a pipeline run.

It is **not** broadly superior to Hermes: Hermes still leads on tool **breadth** (40+ vs 5), **gateway platform
count**, **deploy targets** (SSH/Modal/Daytona), and ~10k-commit **maturity**.

**#1 remaining gap:** **tool breadth + live-validated gateways** — deepen `tools/` and exercise the Telegram/Slack/
Discord adapters with real credentials. That converts "architecture present" into "surface proven."

Full record: `studies/m1frame-v1.3-readiness/` (ROADMAP · QA_GATE · council · FINAL_REPORT).
