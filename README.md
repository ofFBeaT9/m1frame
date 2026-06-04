# m1frame

[![CI](https://github.com/mahdadshakiba/m1frame/actions/workflows/ci.yml/badge.svg)](https://github.com/mahdadshakiba/m1frame/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

**Portable multi-agent AI framework** — 7 pillars, 6 source repositories, one pipeline.  
Works with Claude, OpenAI, Ollama, vLLM, and LM Studio. Switch backends in one line.  
Fully offline-capable. Git-versionable. Zero lock-in.

> **New: [m1frame Studio](#m1frame-studio--watch-the-council-think) 🛰️** — a real-time, zero-build UI where you
> *watch* the council deliberate, the knowledge graph grow, and memory update live. Most agents only show you a
> final answer; m1frame shows you the **reasoning** — the debate, the red-team, the grounding. Run it with no API
> key (gorgeous demo mode) or wire a key for live runs.
>
> Now also **self-improving** (council-**vetted** skills learned from passing runs) and **200+ models** via
> OpenRouter. 📖 **Full guide: [MANUAL.md](MANUAL.md).**

---

## Source Repositories

| Pillar | Source | Role |
|---|---|---|
| **BMAD** | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Agile story backlog — analyst / architect / dev / qa / pm / investigator roles |
| **LLM Council** | [gcpdev/llm-council-skill](https://github.com/gcpdev/llm-council-skill) | Brainstorm before generation + QA review after |
| **Miras** | [ofFBeaT9/miras](https://github.com/ofFBeaT9/miras) | Sequential sub-agent orchestration with full state handoffs |
| **Karpathy Patterns** | [karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Forced `<thought>` chain-of-thought, deterministic prompting |
| **LLM Wiki** | [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) | Persistent three-layer knowledge graph (Analysis→Generation) |
| **OpenPlanter** | [ShinMegamiBoson/OpenPlanter](https://github.com/ShinMegamiBoson/OpenPlanter) | Recursive investigation agent — entity resolution, cross-referencing, dataset ingestion |

---

## Quick Start

```bash
git clone https://github.com/ofFBeaT9/m1frame.git && cd m1frame
pip install -r requirements.txt
cp .env.example .env           # add your ANTHROPIC_API_KEY
python scripts/qa_validate.py  # 43 tests, no key needed
python -m m1frame --goal "Build a FastAPI service with JWT auth"
```

Or with Make:
```bash
make install && make qa
make run GOAL="Investigate vendor payments against lobbying disclosures"
```

---

## m1frame Studio — watch the council think

A premium, **zero-build** single-file UI (`m1frame-studio.html`) that turns the batch pipeline into a live,
interactive **deliberation theatre**. No npm, no bundler, no CDN — it opens offline and renders a bespoke
"deep-observatory" interface.

```bash
pip install fastapi "uvicorn[standard]" httpx      # or: make studio
python studio/build_demo.py                         # build the demo fixture (once)
python api/server.py                                # → open http://localhost:8080
```

Six surfaces, one renderer:

| Surface | What you get |
|---|---|
| **Studio** | Type a goal and watch all 7 pillars work **live** — BMAD stories appear, the Council debates persona-by-persona (Critic · Advocate · Domain Expert + **red-team**) with animated consensus scores, Karpathy streams its `<thought>`, the knowledge graph grows node-by-node, and the miras memory feed pulses. |
| **Chat** | Talk to m1frame — answers stream token-by-token, **grounded** in the wiki with clickable citations. |
| **Graph** | The full force-directed knowledge-graph constellation; click any node to read its page. |
| **Runs** | Every run, fully **replayable** from its recorded event trace. |
| **Skills** | The library of **council-vetted** skills m1frame has learned — score, uses, roles, approach. Self-improving, but auditable. |
| **Wiki** | Search and read the knowledge base with rendered Markdown, types, and confidence. |
| **Settings** | One-click backend/model switch, scheduler, live metrics, demo/live toggle, accent theming. |

**Three tiers, always works:**
1. **FastAPI + API key** → full live runs (real SSE streaming of the pipeline + live chat).
2. **FastAPI, no key** → the server replays a real recorded deliberation over SSE; chat falls back to keyword-grounded retrieval.
3. **No pip at all** → `python studio/serve.py` (stdlib only) serves the UI and the bundled demo replays entirely client-side.

It streams over **Server-Sent Events** from new endpoints (`GET /run/{id}/events`, `POST /chat`,
`GET /wiki/graph`, `GET /metrics.json`, `GET|PATCH /config`). The pipeline instrumentation is fully additive —
`emit=None` by default, so the CLI and the **68/68** QA suite are byte-for-byte unaffected.

### Why m1frame is the most *auditable* multi-agent workspace

This is not a claim that m1frame out-features every agent — Hermes Agent, for one, leads on gateways, tool
breadth, model count, and maturity (see the honest parity matrix in
[`studies/m1frame-studio/ROADMAP.md`](studies/m1frame-studio/ROADMAP.md)). It's a claim about **one axis we lead
on decisively: transparency you can trust.** Most agents show you an answer; m1frame shows you **how it got
there** — **deliberation** you can watch (a multi-persona council + an independent red-team that can *veto* a
pass, both real in `agents/council.py`, not just the UI), **grounding** you can click (a living knowledge graph +
cited chat), and **memory** you can watch accumulate (miras) — all 100% portable, offline-capable, zero-lock-in.

---

## 7-Pillar Pipeline

```
Your Goal
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. BMAD  —  Story Backlog                                   │
│    Scrum Master → ordered stories with roles + AC           │
│    Roles: analyst · architect · dev · qa · pm · investigator│
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Council Brainstorm  (PRE-generation)                     │
│    Critic · Advocate · Domain Expert analyse the goal       │
│    Synthesiser → unified implementation plan + risks        │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. OpenPlanter  —  Investigation Layer                      │
│    Auto-invoked for "investigator" stories                  │
│    Entity resolution · cross-referencing · dataset ingestion│
│    19-tool suite: file I/O, shell, web search, sub-agents   │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Miras  —  Multi-Agent Execution                          │
│    Each story → role-matched sub-agent                      │
│    Full AgentState passed between every handoff             │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Karpathy  —  Chain-of-Thought Refinement                 │
│    Forced <thought> reasoning · two-pass refine             │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Council Review  (POST-generation QA gate)                │
│    Consensus score ≥ 7/10 → approved_output                 │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. LLM Wiki  —  Knowledge Graph                             │
│    Analysis → Generation → interlinked Markdown pages       │
│    entities/ · concepts/ · sources/ · synthesis/            │
└─────────────────────────────────────────────────────────────┘
```

---

## OpenPlanter — Investigation Layer

OpenPlanter is a recursive investigation agent that ingests heterogeneous datasets, resolves entities across them, and surfaces non-obvious connections. In m1frame it runs as Pillar 3 and as a Miras sub-agent for stories with `role: investigator`.

```python
from agents.openplanter import OpenPlanterAgent

op = OpenPlanterAgent(llm_client, workspace="./workspace")

# Full investigation
result = op.investigate("Cross-reference vendor payments against lobbying disclosures")
print(result.report())

# Entity resolution across raw data
entities = op.resolve_entities("Acme Corp paid ACME Inc $500k in Q1 2025")

# Cross-reference two datasets
result = op.cross_reference(dataset_a="vendor_payments.csv", dataset_b="lobbying_db.csv")
```

Supported providers: `anthropic` · `openai` · `openrouter` · `cerebras`  
Optional service keys: `EXA_API_KEY` (web search) · `VOYAGE_API_KEY` (embeddings)

For full 19-tool support, install OpenPlanter directly:
```bash
pip install git+https://github.com/ShinMegamiBoson/OpenPlanter.git
```
Without it, m1frame runs OpenPlanter in **LLM-only mode** (all reasoning, no real file/shell tools).

---

## Switch Backends — One Line

```yaml
# config.yaml
backend: ollama     # claude | openai | openrouter | ollama | vllm | lmstudio
```

`openrouter` reaches **200+ models** (Anthropic, OpenAI, Google, Meta, Mistral, …) through one
OpenAI-compatible endpoint — set `openrouter.model` to e.g. `google/gemini-2.0-flash`. Local backends
(ollama/vllm/lmstudio) need no key and run fully offline.

```bash
python -m m1frame --goal "..." --backend ollama  # fully offline with Ollama
```

---

## Wiki — Three-Layer Architecture

```
wiki/raw/sources/   ← Immutable. You write here. LLM reads only.
wiki/               ← LLM-maintained pages (entities/ concepts/ sources/ synthesis/)
CLAUDE.md           ← Schema: page types, WikiLink conventions, ingest protocol
purpose.md          ← Goals, scope, evolving thesis — the wiki's soul
```

```python
wiki = LLMWiki(client)
wiki.ingest("raw text", topic_hint="topic")   # two-step Analysis→Generation
wiki.query("What connections exist between X and Y?")
wiki.lint()    # health check → LintReport (contradictions, orphans, gaps)
```

---

## QA

```bash
make qa                                         # all 43 tests
python scripts/qa_validate.py --pillar openplanter
python scripts/qa_validate.py --pillar e2e      # full 7-pillar pipeline
```

---

## File Map

```
m1frame/
├── purpose.md              ← Wiki soul
├── CLAUDE.md               ← Wiki schema
├── config.yaml             ← All config — one line to switch backends
├── llm_client.py           ← Unified adapter: Claude / OpenAI-compat / local
├── pyproject.toml          ← Installable: pip install m1frame
├── Makefile                ← make qa · make lint · make run GOAL="..."
├── LICENSE · CONTRIBUTING.md · SECURITY.md · CHANGELOG.md
├── .github/
│   ├── workflows/ci.yml    ← Matrix CI: Ubuntu/macOS/Windows × Py 3.10-3.12
│   ├── ISSUE_TEMPLATE/     ← Bug report + Feature request templates
│   └── pull_request_template.md
├── m1frame-studio.html     ← ⭐ the Studio UI — one zero-build file, six surfaces
├── agents/
│   ├── bmad.py             ← BMADAgent, Blueprint, Story, BMAD_ROLES
│   ├── miras.py            ← MirasOrchestrator, AgentState, ROLE_MAP
│   ├── karpathy.py         ← KarpathyEngine, KarpathyResult
│   ├── council.py          ← LLMCouncil (+ optional persona-stream callbacks)
│   ├── wiki.py             ← LLMWiki, WikiPage, LintReport
│   ├── openplanter.py      ← OpenPlanterAgent, InvestigationResult, Entity
│   └── events.py           ← EventBus — thread-safe progress stream for Studio
├── api/
│   └── server.py           ← FastAPI: REST + SSE (/run/{id}/events, /chat, /wiki/graph…)
├── studio/
│   ├── build_demo.py       ← generates the demo fixture + static snapshots
│   ├── data.py             ← read-only wiki/graph/memory views (no LLM)
│   ├── serve.py            ← stdlib static server (zero-pip demo)
│   └── demo_run.json       ← bundled recorded deliberation
├── wiki/                   ← Auto-created knowledge graph
└── scripts/
    ├── run_workflow.py     ← 7-pillar runner (now emits live progress events)
    └── qa_validate.py      ← 68-test offline QA suite
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Report security issues via [SECURITY.md](SECURITY.md).

---

*m1frame v1.2.0 "Studio + Skills" — Mahdad Shakiba, June 2026* · [Manual](MANUAL.md)
