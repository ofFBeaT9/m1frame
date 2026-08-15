# Changelog

All notable changes to m1frame are documented here.  
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]
### Added — `sensors/` and `optimizers/`: measurement and improvement
Two new modules, integrating [Sentrux](https://github.com/sentrux/sentrux) and
[Microsoft SkillOpt](https://github.com/microsoft/SkillOpt) (both MIT). **Neither is a hard
dependency** — with nothing installed every entry point returns a structured `available: false`
and m1frame behaves exactly as before.

- **`sensors/`** adds an optional, **advisory** structural measurement (via the third-party
  Sentrux CLI, not bundled) — reported alongside the council verdict but **never changing it**
  unless you explicitly set `sensors.enforce: true`. A `sensor_reading` event is emitted at the
  QA gate of every run. Scores 0–10000 across modularity/acyclicity/depth/equality/redundancy,
  rescaled to m1frame's 0–10.
- **`optimizers/`** adds skill improvement, closing the write-once skill library: a skill
  distilled by `learn()` is now optimised after a passing run instead of frozen forever.
  **The default tier is m1frame's own dependency-free hill-climber — not Microsoft's SkillOpt.**
  It shares SkillOpt's accept-on-improvement mechanic; it has no LLM step and has not been
  benchmarked against the SkillOpt paper. When the real `skillopt` package is installed, edits
  are applied by **SkillOpt's own `optimizer.apply_patch`** and the result reports `tier: skillopt`.
- **Surfaces**: tool registry 40 → 47; `GET /sensors`, `POST /sensors/scan`, `GET /optimizers`,
  `POST /skills/{id}/optimize`; MCP tools `m1frame_scan_architecture`, `m1frame_optimize_skill`;
  `sensors:` / `optimizers:` sections in `config.yaml`, honoured identically by all three surfaces.
- **QA 111 → 163 tests**, all passing offline with neither package installed.

### Fixed — Windows / encoding robustness (pre-existing, found by end-to-end verification)
- **`run_workflow()` crashed whenever stdout was not a UTF-8 terminal.** The UTF-8 guard ran only
  in `main()`, but `api/server.py` and `mcp_server.py` import and call `run_workflow` directly, so
  any piped, redirected or server-hosted run died with `UnicodeEncodeError` on the first pillar
  banner. The guard now runs on every entry path, and printing degrades instead of raising.
- **`verbose=False` did not actually silence output** — only 7 of 35 print sites checked it, and
  both servers pass `verbose=False` to keep banners out of their logs. Output now routes through a
  thread-local `say()` (thread-local because the API server can run workflows concurrently). The
  CLI default is unchanged, so CLI output is byte-identical.
- **The wiki layer performed text I/O without naming an encoding**, so on Windows it wrote cp1252
  bytes into UTF-8 files; `wiki/log.md` had become unreadable and pillar 7 could not complete.
  All 26 sites now specify `encoding="utf-8"`, and reads go through a helper that repairs legacy
  cp1252 bytes rather than crashing on an existing workspace.
- A new `encoding` QA pillar (5 tests) pins all of the above; each was confirmed to fail against
  the pre-fix code.

### Fixed — CI lint / type-check (this cycle would have turned CI red)
The QA suite passes on Python 3.13 locally, but CI also runs `ruff check .` and `mypy` across
3.10–3.12. Both were checked before commit and both had regressed:
- **`tools/registry.py`: `def names(self) -> list[str]` resolved `list` to the class's own `list()`
  method, not the builtin.** Latent since the registry was written, and invisible until this cycle
  made `agents/skills.py` import `optimizers`, which pulls `tools/registry.py` into mypy's scope.
  Harmless at runtime under postponed annotations, but it breaks `typing.get_type_hints()` on the
  class. Now annotated `builtins.list[str]`, with a comment so the prefix is not "cleaned up".
- Fixing that unmasked two more: `sensors/tools.py` typed a `None` binary path as `str`, and
  `tools/extra.py` let mypy join 25 distinct handlers into bare `function`, which no longer
  matched `Tool`'s `Callable` field.
- Five Ruff errors: an unsorted import block in `api/server.py`, `E741` (`l`) and a redundant
  `.encode("utf-8")` in the QA suite, and two `UP038` `isinstance` tuples in `sensors/sentrux.py`.
  The QA suite's redundant encoding argument is kept with a `noqa` and a reason — naming the
  encoding is precisely what that test exists to enforce.
- Every file in this commit was additionally re-parsed against the **3.10** grammar, since the dev
  machine is 3.13 and a 3.11+ feature would compile locally while breaking three CI jobs.

### Security / correctness notes for this change
- `POST /skills/{id}/optimize` rewrites a stored skill on disk and therefore **requires
  `approve: true`**, matching the `dangerous` convention used by `write_file` and `sentrux_gate`.
- `rounds`, `timeout` and keyword-list length are clamped at both the HTTP and tool layers, and
  the blocking work runs off the event loop, so one request cannot stall the server.
- Sensor paths are workspace-jailed (null bytes rejected) and the subprocess is `shell=False`
  with a bounded timeout. Reported `command` strings are scrubbed of absolute paths.
- **`pip install sentrux` does not install `github.com/sentrux/sentrux`.** The PyPI package of
  that name is an unaffiliated pure-Python tool (no project URLs, 22 kB, Python-only). The
  adapter detects which one it is driving and reports the flavour; use the Rust project's own
  install path (`brew`/`install.sh`/Releases/`cargo build`) if you want the requested tool.

### Added — phone / internet access without a tunnel
- **GitHub Pages deploy** (`.github/workflows/pages.yml`): publishes the mobile-responsive Studio as a public,
  key-less demo at `https://<owner>.github.io/m1frame/` — open it from any phone over the internet, zero setup.
- **Dispatch-ready**: `mcp` is now a real dependency, so a dispatched cloud Claude Code session gets m1frame's
  tools automatically (`.mcp.json` auto-registers after `pip install -r requirements.txt`). MANUAL §"from your
  phone" documents both no-server paths (Dispatch for the agent, Pages for the UI).

## [1.7.0] — 2026-06-04 — "Pocket Studio" (use m1frame from your phone)
### Added
- **Mobile-responsive Studio**: a phone layout for `m1frame-studio.html` — the left nav rail becomes a
  **bottom tab bar**, the 7-pillar timeline scrolls horizontally, everything goes single-column, the composer
  stacks the RUN button, and it's notch-safe (`env(safe-area-inset-*)`). Verified at 375×812.
- **MCP over HTTP + auto-Studio** (`python mcp_server.py --http` / `make mobile`): serves the MCP server over
  streamable-HTTP so the **Claude app on iPhone/Android** can connect by URL, and **auto-starts the Studio UI**
  (bound to `0.0.0.0`) so the interface loads automatically. Prints both URLs + the exact `claude mcp add` line.
- `m1frame_open_studio` now returns a phone-reachable URL; `M1_STUDIO_BIND` / `M1_STUDIO_HOST` env knobs.
### Notes
- **101/101** offline QA (+2 mobile tests). The MCP HTTP code is import-guarded; `mcp` stays optional.
- ⚠️ `--http` binds `0.0.0.0` with an unauthenticated config-write endpoint — expose only on a trusted network
  or behind an authenticating tunnel.

## [1.6.1] — 2026-06-04 — "Green CI"
### Fixed (CI / lint)
- Made the **CI lint + type-check job green**: applied ~837 safe Ruff autofixes (import sorting, `Optional`→
  `X | None`, unused imports) and hand-fixed the rest (B904 `raise ... from`, E741 `l`→`ln`, B005, UP028/UP038).
- Fixed a **real latent bug** mypy caught: `run_workflow.py` called `metrics.record()` with `score`/`passed`
  kwargs it doesn't accept — would have raised `TypeError` on a *live* council-review step (never hit by
  demos/tests). Now records timing only; score/passed are already logged + emitted.
- Fixed `callable` used as a type annotation in `agents/council.py` (→ `Callable`).
- Ruff: excluded private research/build scripts; per-file-ignore for the intentionally dense QA suite.
- Mypy: `types-PyYAML` in CI; `warn_return_any=false` (noise over untyped LLM SDKs; real errors still fail).

## [1.6.0] — 2026-06-04 — "Claude Code Native"
### Added
- **Claude Code CLI backend** (`claudecli`): m1frame runs on your `claude` login with **no API key** — each
  agent call shells out to `claude -p` headlessly. Added to `config.yaml`, `LOCAL_BACKENDS`, `ALL_BACKENDS`
  (→ 10 backends; `can_run_live` true with no key).
- **MCP server** (`mcp_server.py`, FastMCP/stdio) exposing m1frame to Claude Code: `m1frame_run`, `m1frame_ask`,
  `m1frame_call_tool`, `m1frame_list_tools`, `m1frame_list_skills`, `m1frame_open_studio`. Auto-registered via
  `.mcp.json`; `mcp` dependency is optional (import-guarded).
- **Slash command** `/m1-studio` to launch the UI (alongside the existing `/m1frame` pipeline command).
### Notes
- **99/99** offline QA (added Claude Code backend + MCP server tests). `mcp_server.py` passes `py_compile`.

## [1.5.0] — 2026-06-04 — "Full Toolbelt"
### Added
- **Tool surface 16 → 40** (`tools/extra.py`): encoding/crypto (`md5`, `hex_encode/decode`, `url_encode/decode`,
  `random_string`, `base_convert`), text (`slugify`, `title_case`, `sort_lines`, `dedupe_lines`, `diff_text`,
  `template_render`, `markdown_to_text`, `extract_urls`), data (`json_format`, `csv_to_json`, `yaml_to_json`,
  `stats_summary`), time (`timestamp`, `time_delta`), and sandboxed files (`file_stat`, `head_file`, `grep_files`).
  On par with Hermes by count; still deliberately omits heavier shell/browser/image tools for auditability.
- **Gateway end-to-end validation harness**: a test drives **every** platform webhook (telegram/slack/discord/
  webhook) through the API and asserts the parsed reply + per-platform outbound payload — the full
  inbound→router→outbound loop, proven without real credentials.
### Notes
- **97/97** offline QA (added the 40-tool spot suite + the gateway e2e test). Every tool is pure, offline, and
  workspace-sandboxed; nothing reads or writes outside the repo.

## [1.4.0] — 2026-06-04 — "Toolbelt" (tool breadth + clean public release)
### Added
- **Tool surface 5 → 16**: sandboxed `read_file`/`write_file`/`list_dir` (workspace-jailed), `json_query`,
  `regex_extract`, `base64_encode`/`decode`, `sha256`, `uuid4`, `url_parse`, `convert_temp` — alongside the
  existing calculator/wiki_search/datetime/word_count/http_get.
- **Command-approval gate**: tools can be marked `dangerous` (e.g. `write_file`); `POST /tools/call` rejects them
  with **403** unless `approve: true` — Hermes-style command approval, auditable.
- **Model registry**: `GET /backends` lists all 9 backends with `ready`/key/active status; surfaced in Settings.
### Changed — clean public release
- **Genericized the bundled demo** to a broadly-relatable decision (monolith vs microservices) and rebuilt a
  clean, self-consistent starter **wiki** (0 lint errors/orphans). Removed all project-specific research content
  (Tritone / ternary / SKYWATER SKY130 / OPU / chip-decision) from the public repo so a new user starts clean.
- Shared SSRF guard already centralized in `agents/net.py`.
### Notes
- **95/95** offline QA (added 5 tool tests: encoding, sandboxed FS, path-traversal block, approval gate, backends).

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
