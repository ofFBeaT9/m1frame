# m1frame — The Manual

*A portable, offline-capable multi-agent framework that doesn't just act — it **deliberates, grounds, and
remembers** — with a real-time UI (Studio) that lets you watch it think.*

> **Version 1.5 "Full Toolbelt"** · works with Claude, OpenAI, OpenRouter (200+ models), Nous, Novita, NVIDIA NIM,
> Ollama, vLLM, LM Studio · reachable from Telegram / Slack / Discord / webhook / CLI · tool surface + MCP ·
> persistent runs · one-command Docker.

---

## Table of contents
1. [What m1frame is (and isn't)](#1-what-m1frame-is-and-isnt)
2. [Install & quickstart](#2-install--quickstart)
3. [m1frame Studio — the UI](#3-m1frame-studio--the-ui)
4. [The 7 pillars](#4-the-7-pillars)
5. [The skill-learning loop](#5-the-skill-learning-loop)
6. [Backends & models](#6-backends--models)
7. [Command line](#7-command-line)
8. [REST + SSE API](#8-rest--sse-api)
9. [Knowledge graph & memory](#9-knowledge-graph--memory)
10. [Configuration](#10-configuration)
11. [m1frame vs Hermes Agent (honest)](#11-m1frame-vs-hermes-agent-honest)
12. [Extending m1frame](#12-extending-m1frame)
13. [Troubleshooting & FAQ](#13-troubleshooting--faq)

---

## 1. What m1frame is (and isn't)

m1frame turns a single goal into a **deliberated, grounded, and remembered** result. A goal flows through seven
pillars — BMAD planning → a Council brainstorm → OpenPlanter investigation → Miras multi-agent execution →
Karpathy chain-of-thought refinement → a Council QA gate **with an independent red-team that can veto** → an
LLM-wiki knowledge-graph ingest. Successful runs are distilled into **council-vetted skills** that make the next
run faster and better.

**The differentiator:** m1frame is the **most *auditable* multi-agent workspace** there is. You don't get a black
box — you *watch* the council debate, *watch* the red-team override an overconfident pass, *click* the grounding
in a live knowledge graph, and *see* memory and skills accumulate. All offline-capable, git-versionable, zero
lock-in.

**What it is not:** it is not (yet) a broad replacement for a mature agent *product*. v1.3–1.5 added messaging
gateways, a **40-tool** surface + MCP, persistent runs, and Docker — so it's on par with Hermes by tool *count*,
but Hermes still ships **heavier capabilities** (arbitrary shell, cloud browser, image/TTS) we deliberately omit
for safety/auditability, plus ~10k-commit *maturity*. See [§11](#11-m1frame-vs-hermes-agent-honest) for the honest comparison.

---

## 2. Install & quickstart

```bash
git clone https://github.com/ofFBeaT9/m1frame.git && cd m1frame
pip install -r requirements.txt          # core + Studio API (fastapi/uvicorn/httpx)
cp .env.example .env                      # add ANTHROPIC_API_KEY for live runs (optional)
```

### Three ways to run — pick your tier

| Tier | Command | Needs | What you get |
|---|---|---|---|
| **Full (live)** | `python api/server.py` + a key | pip + API key | Live runs, SSE streaming, live chat, learning |
| **Server demo** | `python api/server.py` | pip only | A real recorded deliberation replays over SSE; grounded keyword chat |
| **Static demo** | `python studio/serve.py` | nothing (stdlib) | The UI + bundled demo replays entirely client-side |

Then open **http://localhost:8080**. No key? The Studio drops into a gorgeous **demo mode** automatically.

```bash
make studio          # installs Studio deps, builds the demo, launches the server
make qa              # 97 offline tests, no key needed
make run GOAL="Build a FastAPI service with JWT auth"   # headless CLI run
```

---

## 3. m1frame Studio — the UI

A single, zero-build, offline file (`m1frame-studio.html`) — hand-built CSS ("deep observatory" theme), no CDN.
Seven surfaces, one event renderer:

| Surface | What it does |
|---|---|
| **Studio** | Type a goal and watch all 7 pillars work **live**: BMAD stories appear, the Council debates persona-by-persona with score rings + the **red-team**, Karpathy streams its `<thought>`, the knowledge graph grows, the miras memory feed pulses, and **skill recall/learned** cards show the self-improving loop. |
| **Chat** | Talk to m1frame; answers stream token-by-token, **grounded** in the wiki with clickable citations. |
| **Graph** | The full force-directed knowledge-graph constellation. Click any node to read its page. |
| **Runs** | Every run, replayable from its recorded event trace. |
| **Skills** | The library of council-vetted skills (score, uses, roles, approach). |
| **Wiki** | Search + read the knowledge base with rendered Markdown, types, and confidence. |
| **Settings** | One-click backend/model switch, scheduler, live metrics, demo/live toggle, accent theming. |

**Keyboard:** `⌘K` / `Ctrl+K` opens the command palette (jump to any surface or run a goal). Fully keyboard
navigable; respects `prefers-reduced-motion`; WCAG-AA contrast.

---

## 4. The 7 pillars

| # | Pillar | File | Role |
|---|---|---|---|
| 1 | **BMAD** | `agents/bmad.py` | A Scrum-Master agent decomposes the goal into an ordered, dependency-aware **story backlog** with roles (analyst/architect/dev/qa/investigator). |
| 2 | **Council (brainstorm)** | `agents/council.py` | Critic · Advocate · Domain Expert analyse the goal *before* generation; a Synthesiser produces one plan. |
| 3 | **OpenPlanter** | `agents/openplanter.py` | Recursive investigation: entity resolution, cross-referencing, dataset ingestion (auto-invoked for `investigator` stories). |
| 4 | **Miras** | `agents/miras.py` | Executes every story with a role-matched sub-agent, full state handed off between them (sequential or `--parallel`). |
| 5 | **Karpathy** | `agents/karpathy.py` | Forced `<thought>` chain-of-thought + optional self-critique to refine the synthesis. |
| 6 | **Council (review)** | `agents/council.py` | A QA gate: the same personas score the output (consensus ≥ 7 → pass), then an **independent red-team** attacks the verdict and can **veto a pass**. |
| 7 | **LLM Wiki** | `agents/wiki.py` | Two-step Analysis→Generation ingest into an interlinked Markdown knowledge graph (`wiki/`). |

The pillars stream structured events over an `EventBus` (`agents/events.py`) — that's what the Studio renders
live. Instrumentation is additive: with no UI attached, behaviour and the test suite are byte-for-byte identical.

---

## 5. The skill-learning loop

m1frame's answer to a "self-improving agent" — with a twist a black-box can't match: **it only remembers what
the council passed.**

- **Learn:** when a run clears the QA gate (score ≥ threshold), the approach is distilled into a `Skill`
  (`agents/skills.py`) — its goal, domain, story roles, recipe steps, the score that earned it, and a usage
  count — saved to `skills/skills.json` (plain JSON you can read and diff).
- **Recall:** on a new goal, `suggest()` keyword-matches prior skills and **seeds BMAD planning** with them, so
  similar goals get better and faster over time. Near-duplicate goals **reinforce** an existing skill (bump
  `uses`) instead of fragmenting the library.
- **Watch it:** the Studio shows a *Skill recall* card at the start of a run and a *Skill learned* card after a
  pass; the **Skills** surface lists the whole library.
- **Why it's better:** every skill is **auditable** — you can see exactly where it came from and why it's
  trusted. Disable per-run with `--no-learn`.

---

## 6. Backends & models

Switch the LLM engine in **one line** (`config.yaml`) or one click (Settings):

```yaml
backend: claude     # claude | openai | openrouter | ollama | vllm | lmstudio
```

| Backend | Models | Key |
|---|---|---|
| `claude` | Claude family | `ANTHROPIC_API_KEY` |
| `openai` | GPT family | `OPENAI_API_KEY` |
| **`openrouter`** | **200+ models** (Anthropic, OpenAI, Google, Meta, Mistral, …) through one endpoint | `OPENROUTER_API_KEY` |
| `ollama` / `vllm` / `lmstudio` | any local model | none (fully offline) |

OpenRouter gives you 200+ models without code changes — set `openrouter.model` to e.g.
`google/gemini-2.0-flash`, `meta-llama/llama-3.3-70b-instruct`, or `openai/gpt-4o`.

---

## 7. Command line

```bash
python -m m1frame --goal "…"            # or: python scripts/run_workflow.py --goal "…"
```

| Flag | Effect |
|---|---|
| `--backend NAME` | Override the configured backend (`claude\|openai\|openrouter\|ollama\|vllm\|lmstudio`) |
| `--parallel` | Run independent Miras stories concurrently |
| `--self-critique` | Use the Karpathy critique→refine loop |
| `--stream` | Stream Karpathy tokens to stdout |
| `--no-council` / `--no-wiki` / `--no-openplanter` | Skip a pillar |
| `--no-learn` | Don't learn/recall a skill this run |
| `--webhook URL` | POST the result JSON on completion |
| `--metrics-port N` | Expose Prometheus `/metrics` on port N |
| `--quiet` | Minimal output |

---

## 8. REST + SSE API

Start: `python api/server.py` → docs at `/docs`.

| Method · path | Purpose |
|---|---|
| `GET /health` | status, backend, `can_run_live` |
| `POST /run` | start a run (`{goal, mode, backend, parallel, self_critique, learn_skills, …}`) → `{run_id, events}` |
| `GET /run/{id}/events` | **SSE** stream of pipeline events |
| `GET /run/{id}` · `GET /runs` | poll / list runs (with recorded event traces) |
| `POST /chat` | **SSE** grounded chat (`{message, ground}`) |
| `GET /wiki/graph` · `GET /wiki/pages` · `GET /wiki/query?q=` | knowledge graph / pages / query |
| `GET /memories` | miras memory snapshot |
| `GET /skills` · `POST /skills/suggest` · `DELETE /skills/{id}` | the skill library |
| `GET\|PATCH /config` | read / switch backend + model |
| `GET /metrics` · `GET /metrics.json` | Prometheus / structured metrics |
| `GET\|POST\|DELETE /schedule` | scheduled investigation jobs |

**Security note:** the server binds `127.0.0.1` by default (it has an unauthenticated config-write endpoint).
Set `HOST=0.0.0.0` only on a trusted network. Webhook URLs are SSRF-filtered (no loopback/private/metadata).

---

## 9. Knowledge graph & memory

- **Wiki** (`wiki/`) — a three-layer knowledge graph (immutable sources → LLM-maintained pages → the schema in
  `CLAUDE.md`). Every page has YAML frontmatter + `[[WikiLinks]]`. Health-check with `python wiki/lint.py`
  (0 errors / 0 orphans). The Studio's Graph and Wiki surfaces read it live.
- **miras** — surprise-gated persistent project memory (decisions, constraints, lessons). Export a snapshot to
  `m1frame/miras_snapshot.json` so the Studio's memory feed shows it.
- **Skills** — `skills/skills.json`, the vetted how-to memory ([§5](#5-the-skill-learning-loop)).

---

## 10. Configuration

Everything lives in `config.yaml`: the backend + per-backend model/keys, pillar settings (BMAD `max_subtasks`,
Council `personas` / `consensus_threshold` / `red_team`, Karpathy CoT, Wiki paths), the API host/port, metrics,
webhooks, the scheduler, and the `studio:` block (default mode, accent, demo speed). Most have sensible defaults;
the only thing you usually touch is `backend:` and your `.env` key.

---

## 11. m1frame vs Hermes Agent (honest)

We benchmark against Nous Research's **Hermes Agent**. The truthful read:

| Axis | Winner |
|---|---|
| Visible, audited, **vetoable** multi-agent deliberation | **m1frame (decisively)** |
| Live knowledge-graph grounding + cited chat | **m1frame** |
| Run replay / auditability (within a session) | **m1frame** |
| Council-**vetted** skill learning (auditable) | **m1frame** (Hermes' loop is broader but black-box) |
| Portability / offline / zero-lock-in | **m1frame** |
| Messaging gateways | **m1frame has them (Telegram/Slack/Discord/webhook/CLI)** · Hermes has more platforms + maturity |
| Tool surface + MCP client | **par by count** (40 auditable tools + approval gate + MCP) · Hermes ships heavier shell/browser/image tools |
| Model count (200+) | par (OpenRouter + Nous/Novita/NIM presets) |
| Deploy | par on **Docker** · Hermes also SSH/Modal/Daytona/Singularity |
| Persistent run history | **m1frame** (disk-backed, searchable, replayable) |
| Maturity (~10k commits) | Hermes |

**Honest headline:** *m1frame is the most **auditable** multi-agent workspace there is.* It is **not** broadly
superior to Hermes across all surface area — and we don't claim "10000×". We lead decisively on transparency you
can trust. **v1.3 closed most of the roadmap in code** — messaging gateways, a tool surface + MCP client, a
persistent run store, more providers, and Docker. What Hermes still owns: raw **tool breadth** (40+ vs our small
auditable set), more **deploy targets** (SSH/Modal/Daytona), more **gateway platforms**, and ~10k commits of
production **maturity**. Those are breadth-and-time gaps, not architecture gaps.

### Gateways — talk to m1frame from anywhere

```bash
python -m gateways                 # local stdin gateway (offline)
python -m gateways --telegram      # Telegram bot (needs TELEGRAM_BOT_TOKEN)
```
Or point any platform's webhook at the API: `POST /gateway/{telegram|slack|discord|webhook}/webhook`. One
`GatewayRouter` handles `/help`, `/status`, `/ping`, `/run <goal>` (full deliberation), and plain text (grounded
chat) — identically on every channel. Outbound replies are SSRF-guarded. Slack URL-verification is handled.

### Tools & MCP

m1frame ships **40 auditable tools** — breadth without a black box. Every one is small, pure, and readable:
- **compute/data:** `calculator` (AST-safe, no `eval`), `json_query`, `json_format`, `csv_to_json`, `yaml_to_json`,
  `stats_summary`, `base_convert`, `regex_extract`, `convert_temp`
- **text:** `slugify`, `title_case`, `sort_lines`, `dedupe_lines`, `diff_text`, `template_render`,
  `markdown_to_text`, `extract_urls`, `word_count`
- **encoding/crypto:** `base64_encode/decode`, `hex_encode/decode`, `url_encode/decode`, `sha256`, `md5`,
  `uuid4`, `random_string`
- **time:** `datetime_now`, `timestamp`, `time_delta` · **web:** `http_get` (SSRF-guarded), `url_parse`
- **knowledge:** `wiki_search` · **files (sandboxed to the workspace):** `read_file`, `head_file`, `list_dir`,
  `file_stat`, `grep_files`, and `write_file` (**dangerous → needs `approve: true`**)

A tool can be marked **`dangerous`**; `POST /tools/call` returns **403** for it unless you pass `approve: true` —
Hermes-style command approval, but auditable. List with `GET /tools`; invoke with `POST /tools/call {"name","args"}`.
Add your own by registering a `Tool`, or attach an **external MCP server**:

```python
from tools import default_registry
from tools.mcp_client import MCPClient
MCPClient().connect_stdio(["python", "my_mcp_server.py"]).register_into(default_registry())  # needs: pip install mcp
```

### Deploy with Docker

```bash
docker compose up --build          # → http://localhost:8080 (demo mode with no key)
```
Volumes persist `wiki/`, `skills/`, and `runs/`. Set keys in `.env`. For a bare host: `python api/server.py`
(bind `HOST=0.0.0.0` only behind auth/network rules — the config-write endpoint is unauthenticated).

---

## 12. Extending m1frame

- **Add a backend:** add a block to `config.yaml` (OpenAI-compatible endpoints just work via `base_url`).
- **Tune the council:** edit `council.personas` / `consensus_threshold` / `red_team` in `config.yaml`.
- **Teach a skill by hand:** add an entry to `skills/skills.json` (it's plain JSON).
- **New event in the UI:** emit it in `scripts/run_workflow.py` and add a `case` in the Studio's `onEvent`.
- **New surface:** add to `NAV` + a `view*()` function in `m1frame-studio.html`.

---

## 13. Troubleshooting & FAQ

- **"Run: pip install fastapi uvicorn httpx"** — install the Studio deps (or `make studio`). The UI still works
  in static demo via `python studio/serve.py`.
- **The UI loads but shows only the background** — a JS error halted boot; open devtools console. (All shipped
  builds are `node --check`-clean and verified in-browser.)
- **LIVE is disabled** — no API key detected; set one in `.env` (or use a local backend). Demo mode needs nothing.
- **Demo says `demo_run.json` missing** — run `python studio/build_demo.py`.
- **Chat/graph empty in static mode** — rebuild snapshots: `python studio/build_demo.py`.
- **Skill not learned** — only runs that *pass* the council gate (score ≥ threshold) are remembered. Check the
  verdict; lower `consensus_threshold` if intentional.
- **Switching backend didn't persist** — `PATCH /config` writes `config.yaml`; ensure the file is writable and
  the model string is simple (`[A-Za-z0-9._/-]`).

---

*m1frame — deliberate · ground · remember. Built to be watched, trusted, and extended.*
