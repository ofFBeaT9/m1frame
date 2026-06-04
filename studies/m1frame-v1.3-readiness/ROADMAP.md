# m1frame v1.3 "Constellation" — Readiness Roadmap

*Pipeline run: BMAD → QA gate → Dev evidence → Council → QA gate → Wiki → Report.*
Topic: **Is m1frame v1.3 production-ready, and what is the #1 remaining gap vs Hermes Agent?**
Evidence anchor: commit `3c3b6f9`, **90/90** offline QA, 9 backends.

---

## 1. Analyst — Project Brief

**Problem.** "Production-ready" and "beat Hermes" have been used loosely across cycles. We need a falsifiable
readiness verdict grounded in what v1.3 actually ships, plus the single highest-leverage next gap — not a wishlist.

**Grounded anchors.**
- v1.3 added (in code, tested): messaging **gateways** (`gateways/`, 5 modules), an agent **tool surface**
  (`tools/`, 4 modules) + MCP client, a **persistent run store** (`runs/<id>.json` + `/runs/search`), 3 more
  **providers** (nous/novita/nvidia_nim → 9 backends), and **Docker** deploy.
- Quality bar: **90/90** offline QA (gateways ×6, tools ×6, run store ×2, deploy ×2 added this cycle).
- Standing memory (do-not-overclaim): m1frame leads decisively on *auditable deliberation*; Hermes leads on
  tool breadth, platform count, deploy targets, and ~10k-commit maturity.

**Core hypothesis.** m1frame v1.3 is **production-ready for its actual positioning** — "the most auditable
multi-agent workspace" — and the **#1 remaining gap is tool *breadth/maturity*** (depth of the `tools/` set and
live-validated gateways), not architecture.

---

## 2. PM — PRD

**Goal.** Decide GO / GO-WITH-CONDITIONS / NO-GO on calling v1.3 production-ready, and name the one top gap.

**Functional requirements (what "ready" means here).**
- FR1 — Core pipeline + Studio run clean and are verifiable offline (no key).  ✅ 90/90 QA, browser-verified.
- FR2 — New subsystems are *additive*: a gateway/tool/persistence failure can never break a run.  ✅ all best-effort/guarded.
- FR3 — Claims in docs are honest and axis-qualified (no "10000×").  ⟵ council to audit.
- FR4 — Security posture stated (localhost bind, SSRF guard, unauth config-write documented).  ✅ shared `agents/net.py`.

**Non-functional.** Offline-first; zero new hard deps for core; portable; reproducible demo.

**Success metrics.** QA = 100% pass; 0 wiki lint errors/orphans; council consensus ≥ 7/10; red-team finds no
unfixed BLOCKER; docs contain no overclaim.

**Out of scope (explicit).** Matching Hermes' 40+ tool *breadth*; live Telegram/Slack credential testing;
SSH/Modal/Daytona deploy targets; ~10k-commit maturity. These are breadth/time, tracked not closed.

---

## 3. Architect — Technical Design (falsifiable)

- **Isolation invariant.** Every Cycle-D entry point (`/gateway/*`, `/tools/*`, `_persist_run`) is wrapped so an
  exception degrades to a message/no-op, never a 500 that aborts a pipeline run. *Falsify:* force each to raise →
  run still completes. (Covered: `t_gw_handler_never_crashes`; persistence/learn in `try/except`.)
- **One SSRF policy.** API webhooks + gateway outbound + `http_get` all call `agents.net.safe_url`. *Falsify:*
  loopback/private/file URLs must be blocked everywhere. (Covered: `t_tool_http_ssrf`, webhook tests.)
- **Persistence correctness.** Atomic write (tmp+`os.replace`); reload is partial-tolerant; search is substring
  over goal+output. *Falsify:* kill mid-write → no corruption; reload a partial file → no crash.
- **Provider routing.** Any non-claude backend routes through the OpenAI-compatible adapter via `base_url`;
  presets only add config. *Falsify:* `load_config()` exposes nous/novita/nvidia_nim with http base_urls. (Covered.)

---

## 4. Scrum Master — Epic + Stories

**Epic:** "Certify v1.3 production-ready and name the top gap."

| # | Story | Acceptance criteria | State |
|---|---|---|---|
| S1 | Re-run full QA | 90/90 pass, 0 errors | ✅ |
| S2 | API smoke of v1.3 surfaces | /health=1.3.0, /tools×5, /gateway 5 platforms, calc=42 | ✅ |
| S3 | Isolation audit | each new subsystem guarded; run survives a forced error | ✅ (tested) |
| S4 | Honesty audit (docs) | vs-Hermes table axis-qualified; no "10000×" | ✅ (council) |
| S5 | Council + red-team | consensus ≥7; no unfixed BLOCKER | ✅ |
| S6 | Wiki ingest + lint | synthesis page added; 0 errors/0 orphans | ✅ |
| S7 | Name the #1 gap | single, evidence-backed | ✅ tool breadth/maturity |
