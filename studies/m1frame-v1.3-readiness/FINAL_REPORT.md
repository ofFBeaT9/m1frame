# FINAL REPORT — m1frame v1.3 "Constellation" Readiness

**Date:** 2026-06-04 · **Commit:** `3c3b6f9` · **Pipeline:** BMAD → QA₁ → Dev/evidence → Council(3)+Red-team → QA₂ → Wiki → Report

---

## Verdict

> **GO — m1frame v1.3 is production-ready *for its positioning*: "the most auditable multi-agent workspace there
> is."** Council consensus **8.3/10**; **90/90** offline QA; **0** wiki-lint errors; no unfixed red-team blocker.
>
> It is **NOT** broadly superior to Hermes Agent. v1.3 closes the *architecture* gaps (gateways, tools, persistent
> runs, providers, Docker) **in tested code**; Hermes still leads on tool **breadth**, **platform/deploy count**,
> and ~10k-commit **maturity**.

## Evidence
| Check | Result |
|---|---|
| Offline QA suite | **90/90** (gateways 6 · tools 6 · run store 2 · deploy 2 · skills 6 · core 68) |
| API `/health` | version **1.3.0** |
| Tool surface | 5 built-ins; `calculator(6*7)=42` via `POST /tools/call` |
| Gateways | 5 platforms `[telegram, slack, discord, webhook, cli]`; telegram `/ping` routed |
| Backends | **9** (claude, openai, openrouter, nous, novita, nvidia_nim, ollama, vllm, lmstudio) |
| Isolation | a raising gateway handler is caught (`t_gw_handler_never_crashes`); skills/persistence wrapped |
| Security | one SSRF policy (`agents/net.py`); loopback/`file://` blocked (`t_tool_http_ssrf`) |
| Wiki | +2 pages, lint **0 errors / 0 orphans** (18 titled, 212 links) |

## What the council changed (fix, don't caveat)
1. `/run` command tightened to a word boundary (no `/runner` misfire) — `gateways/router.py` + `api/server.py`.
2. Docs vs-Hermes table rewritten to axis-qualified rows; "roadmap" → "closed in code; breadth/maturity remain."
3. Stale miras positioning ("gateways/tools/deploy = roadmap") flagged for update (done at report time).

## Caveats (honest)
- The 3 non-CLI gateways and the MCP client are **architecture-complete but not live-credential-tested** offline.
- The tool set is intentionally **small + auditable** (5), not Hermes' 40+.
- `_load_persisted_runs()` runs per `create_app()`; fine now, candidate for a per-instance store later.

## The single highest-priority remaining gap
**Tool breadth + live-validated gateways.** Deepen `tools/` (file/search/code tools) and exercise the
Telegram/Slack/Discord adapters end-to-end with real tokens. This converts "architecture present" into "surface
proven" — the last thing between m1frame and a head-to-head with Hermes on its own turf.

## Next steps
1. Add 8–12 more built-in tools + a guided gateway setup (`/platforms`-style).
2. Stand up a real Telegram bot in CI-lite to validate the adapter loop.
3. A model-registry UI in Settings (we have 9 backends; surface them with health checks).
