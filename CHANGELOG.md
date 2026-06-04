# Changelog

All notable changes to m1frame are documented here.  
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]
_No unreleased changes yet._

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
