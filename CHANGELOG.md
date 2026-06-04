# Changelog

All notable changes to m1frame are documented here.  
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]
_No unreleased changes yet._

## [1.3.0] — 2026-06-04 — "Constellation" (close the Hermes gap)
### Added
- **Messaging gateways** (`gateways/`): one transport-agnostic `GatewayRouter` (local `/help` `/status`
  `/ping` commands; `/run` → full deliberation; plain text → grounded chat) behind **Telegram / Slack /
  Discord / generic-webhook / CLI** adapters (pure parse/format fns + real delivery). API:
  `POST /gateway/{platform}/webhook` (SSRF-guarded, Slack URL-verification), `GET /gateway/status`.
  Run a local gateway with `python -m gateways` or a Telegram bot with `python -m gateways --telegram`.
- **Agent tool surface** (`tools/`): `ToolRegistry` + auditable built-ins (safe AST `calculator`,
  `wiki_search`, `datetime_now`, `word_count`, SSRF-guarded `http_get`) + an MCP-client connector for
  external MCP servers. API: `GET /tools`, `POST /tools/call`.
- **Persistent run store**: completed runs are written atomically to `runs/<id>.json`, reloaded on
  startup, and searchable via `GET /runs/search?q=` — Runs history now survives restarts.
- **More providers**: `nous`, `novita`, `nvidia_nim` presets (OpenAI-compatible) alongside `openrouter`.
- **Docker deploy**: `Dockerfile` + `docker-compose.yml` (+ `.dockerignore`) — `docker compose up` serves
  the Studio on :8080 with volumes for `wiki/`, `skills/`, `runs/`.
- Shared SSRF guard factored into `agents/net.py` (one policy for the API + gateways).

### Notes
- **90/90** offline QA (added 16 tests: gateways ×6, tools ×6, run store ×2, deploy ×2). All new subsystems
  are additive and best-effort — a gateway/tool/persistence error can never break a pipeline run.
- Honest positioning unchanged: m1frame now **closes the gateway/tool/deploy gaps in code**, but Hermes still
  leads on tool *breadth* and production maturity. See MANUAL §11.

## [1.2.0] — 2026-06-04 — "Studio + Skills"
### Added
- **Council-vetted skill-learning loop** (`agents/skills.py`): runs that pass the QA gate (score ≥ threshold)
  are distilled into reusable, auditable `Skill`s (`skills/skills.json`); `suggest()` recalls them to seed BMAD
  planning on similar goals, so the system improves over time. Near-duplicate goals reinforce instead of
  fragmenting. Wired into `scripts/run_workflow.py` (`--no-learn` to disable) and emitted as
  `skill_suggested` / `skill_learned` events.
- **OpenRouter backend** — 200+ models through one OpenAI-compatible endpoint (`config.yaml`, `OPENROUTER_API_KEY`).
- **Studio "Skills" surface** + live skill-recall / skill-learned cards; API `GET /skills`,
  `POST /skills/suggest`, `DELETE /skills/{id}`.
- **[MANUAL.md](MANUAL.md)** — a complete user manual (pillars, Studio, skills, backends, CLI, API, vs Hermes).

### Notes
- 73/73 offline QA (added 5 skill tests). Skill learning is opt-out and never runs in the test suite.

## [1.1.0] — 2026-06-03 — "Studio"
### Added
- **m1frame Studio** (`m1frame-studio.html`) — a zero-build, offline, single-file real-time UI with six
  surfaces: live Studio deliberation, grounded Chat, the knowledge-graph constellation, replayable Runs,
  a Wiki reader, and Settings (backend switch, scheduler, metrics, theming).
- **Streaming engine** — `agents/events.py` `EventBus` (thread-safe fan-out) + new FastAPI SSE endpoints
  `GET /run/{id}/events`, `POST /chat`, plus `GET /wiki/graph`, `GET /memories`, `GET /metrics.json`,
  and `GET|PATCH /config`. The UI is served from `GET /`.
- **Demo/replay mode** — `studio/build_demo.py` records a real deliberation to `studio/demo_run.json`
  (+ static snapshots) so the UI is fully alive with **no API key and no pip** (`studio/serve.py`).
- Pipeline progress instrumentation in `scripts/run_workflow.py` + optional persona-stream callbacks in
  `agents/council.py` — all additive (`emit=None` default), so existing behaviour is unchanged.

### Changed
- `requirements.txt` installs the Studio API deps; `Makefile` adds `make studio` / `make demo`.

### Notes
- The 68/68 offline QA suite passes unchanged — instrumentation is byte-for-byte transparent when unwatched.

---

## [1.0.0] — 2026-05-06

### Added

**Five pillars integrated from their source repositories:**

- **BMAD** (`agents/bmad.py`) — Agile story backlog with 6 role types (`analyst`, `architect`, `dev`, `qa`, `scrum_master`, `pm`), acceptance criteria per story, and blueprint validation. Source: [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD)

- **LLM Council** (`agents/council.py`) — Two-mode system: `brainstorm()` consults personas *before* generation (Critic, Advocate, Domain Expert); `review()` runs QA gate *after* generation with consensus scoring. Synthesiser is a separate aggregation step. Source: [gcpdev/llm-council-skill](https://github.com/gcpdev/llm-council-skill)

- **Miras Orchestrator** (`agents/miras.py`) — Sequential sub-agent routing with full `AgentState` passed between every handoff. Each story routed to its BMAD-role-matched sub-agent. Dependency order enforced at runtime. Source: [ofFBeaT9/miras](https://github.com/ofFBeaT9/miras)

- **Karpathy Patterns** (`agents/karpathy.py`) — Forced `<thought>` chain-of-thought, temperature 0.1 for deterministic reasoning, optional two-pass `refine=True`, few-shot prompt builder. Source: [karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

- **LLM Wiki** (`agents/wiki.py`) — Three-layer Karpathy architecture: `raw/sources/` (immutable), `wiki/` (LLM-owned), `CLAUDE.md` (co-evolved schema). Two-step Analysis→Generation ingest. `query()`, `lint()`, `search()` operations. Auto-generated `overview.md`, append-only `log.md`. Source: [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki)

**Unified LLM client** (`llm_client.py`) — Single adapter for Claude (Anthropic SDK), OpenAI, Ollama, vLLM, LM Studio. Switch backends with one line in `config.yaml`.

**Release infrastructure:**
- `pyproject.toml` — installable Python package (`pip install m1frame`)
- `python -m m1frame --goal "..."` entry point
- GitHub Actions CI — matrix tests on Ubuntu/macOS/Windows × Python 3.10/3.11/3.12
- Offline QA suite — 34 tests, zero API key required (`python scripts/qa_validate.py`)
- `Makefile` — standard dev commands (`make qa`, `make lint`, `make run GOAL="..."`)
- `LICENSE` (MIT), `CONTRIBUTING.md`, `SECURITY.md`
- Issue templates (Bug Report, Feature Request) and PR template
- Pinned dependencies for deterministic builds

### Security
- Output passed to user message not system prompt in Council review — prevents system-prompt overflow on large outputs
- API keys sourced from environment only — never hardcoded

- **OpenPlanter** (`agents/openplanter.py`) — Pillar 7: recursive investigation agent. Entity resolution, cross-referencing, dataset ingestion. Auto-invoked for BMAD `investigator` stories. LLM-only mode without OpenPlanter installed; full 19-tool mode with `pip install git+https://github.com/ShinMegamiBoson/OpenPlanter.git`. Source: [ShinMegamiBoson/OpenPlanter](https://github.com/ShinMegamiBoson/OpenPlanter)

- **`investigator` BMAD role** — new role in `BMAD_ROLES` and `ROLE_MAP` for investigation-type stories

### Known limitations (v1.0.0)
- Wiki `overview.md` regeneration is heuristic — quality varies by model (`# BETA`)
- Karpathy `refine=True` doubles token usage (`# BETA`)
- `vector_store: lancedb` in `config.yaml` requires optional install: `pip install m1frame[vector]`

---

[Unreleased]: https://github.com/mahdadshakiba/m1frame/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/mahdadshakiba/m1frame/releases/tag/v1.0.0
