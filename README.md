# m1frame

[![CI](https://github.com/ofFBeaT9/m1frame/actions/workflows/ci.yml/badge.svg)](https://github.com/ofFBeaT9/m1frame/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

**Portable multi-agent AI framework** — 7 pillars, 8 source repositories, one pipeline.  
Works with Claude, OpenAI, **OpenRouter (200+ models)**, Nous, Novita, NVIDIA NIM, Ollama, vLLM, and LM Studio. Switch backends in one line.  
Reach it from **Telegram / Slack / Discord / webhook / CLI**, give it **tools**, deploy with **Docker**.  
Fully offline-capable. Git-versionable. Zero lock-in.

> **New: [m1frame Studio](#m1frame-studio--watch-the-council-think) 🛰️** — a real-time, zero-build UI where you
> *watch* the council deliberate, the knowledge graph grow, and memory update live. Most agents only show you a
> final answer; m1frame shows you the **reasoning** — the debate, the red-team, the grounding. Run it with no API
> key (gorgeous demo mode) or wire a key for live runs.
>
> Now also **self-improving** (council-**vetted** skills learned from passing runs), **200+ models** via
> OpenRouter, **messaging gateways** (Telegram/Slack/Discord/webhook), a **47-tool** agent surface, and
> **persistent run history** — deployable with one `docker compose up`.
>
> **New in v1.8.0 — [`sensors/` & `optimizers/`](#sensors--optimizers--the-two-modules-that-close-the-loop)
> close two open loops.** The council could argue about quality but never **measure** it, and a learned
> skill was **frozen at birth**. Now an objective structural score is reported beside every verdict
> (advisory — it never overrules the council unless you say so), and a distilled skill is rewritten and
> kept **only when it scores better**. Both are optional: install nothing and the pipeline is unchanged.
>
> **Claude Code native** 🤝 — run m1frame on your Claude Code login with **no API key** (`backend: claudecli`),
> and an **MCP server** gives Claude Code m1frame as tools. **📱 Use it from your phone** — `make mobile` serves
> MCP over HTTP + the **mobile-responsive Studio**, so the Claude app (iPhone/Android) connects by URL and the UI
> loads automatically. 📖 **Full guide: [MANUAL.md](MANUAL.md).**

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
| **Sentrux** *(optional)* | [sentrux/sentrux](https://github.com/sentrux/sentrux) | Structural **measurement** of the artefact — an objective score beside the council's subjective one |
| **SkillOpt** *(optional)* | [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) | Skill **improvement** — bounded edits kept only when they score better |

---

## Quick Start

```bash
git clone https://github.com/ofFBeaT9/m1frame.git && cd m1frame
pip install -r requirements.txt
cp .env.example .env           # add your ANTHROPIC_API_KEY
python scripts/qa_validate.py  # 164 tests, no key needed
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

Seven surfaces, one renderer:

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
`emit=None` by default, so the CLI and the **164/164** QA suite are byte-for-byte unaffected.
On a phone it's fully responsive — the rail becomes a bottom tab bar (run `make mobile` for phone access).

### Why m1frame is the most *auditable* multi-agent workspace

This is not a claim that m1frame out-features every agent — Hermes Agent, for one, still leads on tool **breadth**
and production **maturity** (see the honest parity matrix in [the manual](MANUAL.md#11-m1frame-vs-hermes-agent-honest)).
It's a claim about **one axis we lead on decisively: transparency you can trust.** Most agents show you an answer; m1frame shows you **how it got
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
│                                                             │
│    ◈ sensors/  — OBJECTIVE measurement joins here           │
│      Sentrux scores the artefact 0–10000 → 0–10 and is      │
│      fused with the council's score. Advisory by default:   │
│      always reported, never changes the verdict unless      │
│      you set sensors.enforce: true                          │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. LLM Wiki  —  Knowledge Graph                             │
│    Analysis → Generation → interlinked Markdown pages       │
│    entities/ · concepts/ · sources/ · synthesis/            │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ ◈ optimizers/  —  the run teaches the next one              │
│    On a PASSING run, skills.learn() distils a skill, then   │
│    optimizers rewrites it under a scorer and keeps the edit │
│    ONLY if it scores better. Skills stop being frozen at    │
│    the quality of the run that produced them.               │
└─────────────────────────────────────────────────────────────┘

◈ = optional module. Nothing installed → structured `available: false`,
    and the pipeline behaves exactly as it did before.
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

## `sensors/` & `optimizers/` — the two modules that close the loop

Before these, the pipeline could deliberate and it could remember — but it could not **measure
what it built**, and a skill it learned was **frozen at birth**. Both are feedback loops that were
open. These two modules close them.

**Neither is a hard dependency.** With nothing installed, every entry point returns a structured
`available: false` and m1frame behaves exactly as before — same output, same QA suite, byte for byte.

### What they do

| | `sensors/` | `optimizers/` |
|---|---|---|
| **Closes** | the *measurement* loop | the *learning* loop |
| **Question** | "is the artefact actually well-structured?" | "can this skill be written better?" |
| **Attaches to** | Pillar 6, the QA gate | after a passing run, when `skills.learn()` distils a skill |
| **Judged by** | measurement (0–10000 → 0–10) | a scorer — the edit is kept **only if it scores higher** |
| **Backed by** | [Sentrux](https://github.com/sentrux/sentrux) CLI (Rust, MIT, not bundled) | m1frame's own hill-climber, or [SkillOpt](https://github.com/microsoft/SkillOpt) if installed |

### Why this improves the architecture

**A council is a room full of opinions.** Every quality signal m1frame had was an LLM arguing with
other LLMs — persuasive, but subjective, and unfalsifiable. `sensors/` adds the one thing a
deliberation cannot produce: a number derived from the artefact itself, computed by a tool with no
opinion. A verdict now shows *both*, and says which is which:

```
council 8.00/10 -> PASS
structural 8.264/10 -> PASS
advisory (enforce=False) -> reported only, council verdict stands -> PASS
```

**It is advisory on purpose.** A measurement may not quietly overrule a judgement, in *either*
direction — a good structure must not upgrade a `CONCERNS`, and a bad one must not downgrade a
`PASS`. Otherwise installing a binary would silently change the meaning of every run in an
existing workspace. `sensors.enforce: true` grants a real veto; it is opt-in and visible in
`GateVerdict.enforced`.

**Skills were write-once.** `skills.learn()` distilled a skill from a passing run and then froze it
forever at that run's quality — a learning system that only ever learned once per skill.
`optimizers/` makes each skill improvable under a scorer, with **strict improvement only**: if no
edit scores better, nothing is persisted (`persisted: false`). The library can get better; it
cannot get worse.

### How to use

Config — one section each, honoured identically by CLI, HTTP API and MCP:

```yaml
sensors:
  enabled: true
  enforce: false          # true = the measurement can veto a passing council
  pass_threshold: 7.0
optimizers:
  enabled: true
  prefer: skillopt        # skillopt | local  (falls back to local automatically)
  rounds: 12
  seed: 1337              # deterministic
```

Python:

```python
from sensors.tools import client, gate
from optimizers import SkillOptimizer

reading = client().scan("agents")             # never raises — a sensor informs a run, never kills one
verdict = gate().fuse(council_score=8.0, result=reading)
print(verdict.verdict, verdict.structural_score, verdict.reasons)

result = SkillOptimizer(seed=1337).optimize(skill_text, scorer, rounds=12)
print(result.tier, result.before_score, "->", result.after_score, result.persisted)
```

HTTP (4 routes) and MCP (2 tools):

```bash
curl localhost:8080/sensors                     # installed? which flavour?
curl -X POST localhost:8080/sensors/scan -d '{"path":".","council_score":8.5}'
curl localhost:8080/optimizers                  # active tier: local | skillopt
curl -X POST localhost:8080/skills/<id>/optimize -d '{"approve":true}'
# MCP: m1frame_scan_architecture · m1frame_optimize_skill
python scripts/qa_validate.py --pillar sensors --pillar optimizers
```

Rewriting a stored skill is a real disk write, so `POST /skills/{id}/optimize` **requires
`approve: true`**. Sensor paths are workspace-jailed, the subprocess is `shell=False` with a
bounded timeout, and `rounds`/`timeout` are clamped at both the HTTP and tool layers.

### Honest limits

> **The Rust sensor needs a `.sentrux/rules.toml` in the scanned directory.** Verified against the
> real binary, built from source (v0.5.7): `check` — the only headless, side-effect-free command
> that prints a score — exits 1 with no output without one. You get a reported reason, not a silent
> zero. With it, a real run reads `Quality: 8264` → `8.264/10`. The tool's intended agent interface
> is its MCP server (`sentrux mcp`, 9 tools); **m1frame does not consume that yet** — that is the
> next real piece of work here.

> **The default optimizer tier is m1frame's own hill-climber, not Microsoft's SkillOpt.** It shares
> SkillOpt's accept-on-improvement mechanic; it has no LLM step and has not been benchmarked
> against the SkillOpt paper. With `skillopt` installed, edits are applied by SkillOpt's own
> `optimizer.apply_patch` and the result reports `tier: skillopt`. On 2 objectives × 40 matched
> seeds the SkillOpt tier wins 55–13 with 12 ties — the cause is structural, not statistical: its
> `EditOp` vocabulary includes `insert_after`, a positional splice the local tier cannot perform.

> ⚠️ **`pip install sentrux` does not install `github.com/sentrux/sentrux`.** The PyPI package of
> that name is an unaffiliated pure-Python tool (no project URLs, Python-only, no MCP server or
> GUI). The adapter detects which one it is driving and reports the flavour. For the Rust project
> use its own install path (`brew` / `install.sh` / Releases / `cargo build --release`).

---

## QA

```bash
make qa                                         # 164 offline tests, no API key
python scripts/qa_validate.py --pillar sensors
python scripts/qa_validate.py --pillar optimizers
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
├── sensors/                ← ◈ optional structural MEASUREMENT (Sentrux adapter)
│   ├── sentrux.py          ← SentruxClient, SensorResult — never raises into a run
│   ├── gate.py             ← StructuralGate — fuses measurement with the council verdict
│   └── tools.py            ← config-honouring constructors + registered tools
├── optimizers/             ← ◈ optional skill IMPROVEMENT (strict-improvement-only)
│   ├── local.py            ← dependency-free hill-climber (the default tier)
│   ├── skillopt.py         ← binds Microsoft SkillOpt's optimizer.apply_patch when present
│   └── tools.py            ← tier selection + registered tools
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
    └── qa_validate.py      ← 164-test offline QA suite (--pillar to run one group)
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Report security issues via [SECURITY.md](SECURITY.md).

---

*m1frame v1.8.0 "Closed Loop" — Mahdad Shakiba, August 2026* · [Manual](MANUAL.md)
