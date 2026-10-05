# m1frame — full module status

Audited October 4, 2026. This is an evidence-based readiness chart, not a claim of perfection.

**Verification:** 164 core checks + 87 regression tests passed (251 total); repository-wide lint and type checking passed. Plugin protocol/lifecycle checks and one upgrade-preservation test passed. Wheel building passed. GitHub CI passed all nine OS/Python combinations and both plugin checks on code commit `3dbb31f`. [Core CI](https://github.com/ofFBeaT9/m1frame/actions/runs/37238064149) · [Plugin CI](https://github.com/ofFBeaT9/m1frame/actions/runs/37238064113). Real optional-module probes are distinguished from offline fixtures.

**Current live blocker:** the configured model provider returns HTTP 403. A prior run completed but failed council approval; it is not counted as a current live pass. Exa/Voyage credentials and a local classifier endpoint are also missing.

**Repairs:** corrected the overriding local MCP launch configuration; added runtime identity; made compression avoid implicit ML downloads; tightened classifier parsing and streamed output checks; preserved merged-entity aliases/sources; honored investigation output directories and prevented file collisions; surfaced enrichment errors; saved all raw wiki sources without a third generation call; implemented complete MCP tool pagination; clarified authentication errors and timeouts; repaired garbled role labels; expanded regression discovery and CI. Runtime code was backed up before deployment, with credentials/configuration preserved.

“Verified live” means an actual local SDK/service/tool was exercised on the described fixture. It does not mean every input or scientific workflow is certified. “Verified offline” uses controlled fixtures/mocks where stated. “Blocked” identifies required external setup. “Partial” records an explicit scope or verification limit.

| Module | Category | Status | Evidence / limit |
|---|---|---|---|
| BMAD planning | Core | Verified offline | Blueprint structure, roles, dependency ordering and invalid-plan rejection pass; earlier live trace traversed planning. |
| Miras orchestration | Core | Verified offline | Sequential/parallel scheduling, state handoff and story failure propagation pass. |
| Karpathy refinement | Core | Verified offline | Response parsing, batching, streaming and self-critique paths covered; earlier live trace completed refinement. |
| Council + red team | Core | Verified offline | Thresholds, invalid scores, vetoes and rejection handling pass. Earlier live score 7/10 was rejected correctly. |
| Complete live workflow | Core | Blocked | Current provider returns HTTP 403 twice. Earlier run completed but was not approved; no current all-green live result. |
| OpenPlanter investigation | Core | Verified offline | Actual registered tool loop tested. Fixed configured workspace, colliding outputs, and invisible integration errors. Local adapter, not upstream shell engine. |
| Wiki ingestion | Core | Verified offline | Two model passes, immutable named/unnamed raw input, index/log/overview and rejected-output exclusion tested. No live approved ingest in this audit. |
| Wiki schema/knowledge quality | Core | Partial | Prompts request source links and metadata; exhaustive claim provenance and all graph constraints are not mechanically guaranteed. |
| Semantic wiki / LanceDB | Optional | Verified live | Real local embedding and database: automobiles retrieved a page about cars; two upserts retained one row. |
| Learned skills | Core | Verified offline | Learning threshold, recall, persistence, deduplication and concurrent writes tested. Quality still depends on council judgment. |
| Tool loop | Core | Verified offline | Real calculator observations, tool budgets, result bounds and approval denial tested. Model text cannot authorize a write. |
| Tool registry + utilities | Core | Verified offline | 54 registered tools discovered. Representative data/text/file tests, path restrictions and explicit write approval pass. |
| External MCP connector | Optional | Verified offline | Real fixture subprocess roundtrip, timeout, cleanup, approval, paginated discovery and repeated-cursor failure tested. |
| MCP plugin + launcher | Core | Verified live | Fresh managed connection: nine MCP tools, OpenRouter configuration, correct isolated interpreter. Fixed project override locally. |
| Runtime upgrades | Core | Verified offline | Backup/preserve regression passes. Applied repairs with credentials and configuration hashes unchanged. |
| Studio browser | Core | Verified offline | Browser regression passes with mocked responses: full/quick modes, history, errors, mobile layout and safe graph tooltips. |
| REST + SSE + saved runs | Core | Verified offline | Request bounds, explicit live failures, saved replay termination and final-output propagation tested. |
| Scheduler | Core | Verified offline | Job persistence, execution, removal, disabling and rescheduling tests pass; production recurring job not scheduled. |
| Events / logging / metrics | Core | Verified offline | Event fanout, terminal events, JSONL traces, timing and Prometheus output covered. |
| Rule guardrails | Core | Verified offline | Input/output rules and approvals pass. Guarded streaming now checks the complete output before release. |
| ShieldGemma classifier | Optional | Blocked | Malformed-reply fail-closed regression added. No responding endpoint on localhost:1234; classifier model is not provisioned. |
| SSRF + file boundaries | Core | Verified offline | Redirect/private-network, traversal, symlink, static-file and approval regressions pass. |
| Context budget guard | Core | Verified offline | Unicode accounting, output reserve, unknown model windows and request-size rejection pass. |
| Headroom compression | Optional | Verified live | Real SDK compressed fixture from 2428 to 836 tokens (65.6% saved), preserving system/latest user. ML download disabled by default; explicit opt-in remains. |
| ADHD output formatter | Optional | Verified offline | Opt-in formatting and structured-content preservation pass; disabled by default. |
| Local skill optimizer | Optional | Verified offline | Deterministic bounded proposals and score-based acceptance covered. Lexical gain is not proof of better reasoning. |
| SkillOpt integration | Optional | Verified live | Real installed package improved fixture objective from -0.06 to 0.96. |
| Sentrux architecture | Optional | Verified live | Official installed sensor scanned agents: 8380/10000. Architecture signal, not model-answer correctness. |
| Scientific catalog | Optional | Verified live | 163 installed entries parse with zero catalog errors; discovery and read regression tests pass. |
| Scientific experiments | Optional | Partial | Catalog instructions are available. Domain-specific datasets, hardware, packages and experiments are not collectively certified. |
| Host Miras memory | Optional | Verified live | Host context request responded; current default project contains no memories. Separate from Python orchestration. |
| Exa web enrichment | Optional | Blocked | Installed exa-py 2.25.0. No EXA_API_KEY; no authenticated search performed. Failures now appear in investigation diagnostics. |
| Voyage entity matching | Optional | Blocked | Installed voyageai 0.5.0. No VOYAGE_API_KEY. Fixture proves merges preserve every alias/source and conservative confidence. |
| Messaging gateways | Optional | Partial | Telegram/Slack/Discord/webhook/CLI parsing, formatting and routing covered offline. No external message was sent. |
| OpenRouter provider | Provider | Blocked | Existing free-only provider returned HTTP 403: Access denied by security policy, on probe and recheck. Account/network action required. |
| Claude API | Provider | Blocked | No configured workspace credential. Added clear preflight error and bounded SDK timeout/retries; no live provider test. |
| Claude CLI | Provider | Partial | CLI adapter isolation and error handling tested offline; current authenticated generation not verified. |
| OpenAI / Nous / Novita / NVIDIA | Provider | Partial | OpenAI-compatible adapter covered by fixtures. Each provider requires its own configured account/model; not live-certified. |
| Ollama / vLLM | Provider | Partial | Compatible adapter paths exist; no live inference service verified in this audit. |
| LM Studio | Provider | Blocked | Configured local endpoint refused connections; installed CLI timed out starting its daemon. Local service repair required. |
| Wheel packaging | Delivery | Verified offline | Wheel builds successfully. Fresh-environment deployment across every optional service remains a separate setup task. |
| Cross-platform CI | Delivery | Verified offline | GitHub CI passed on code commit 3dbb31f: all nine Windows/macOS/Linux × Python 3.10/3.11/3.12 jobs, lint/type checks, and both plugin platform checks. |
| Autonomous code/test execution | Scope | Partial | The framework plans, reviews and calls bounded tools. Arbitrary shell execution and unattended write approval are not part of its current tool loop; use host development tools. |

## Reproduce

```text
python scripts/qa_validate.py
python -m unittest discover -s scripts -p "test_*.py"
ruff check .
mypy agents/ llm_client.py --ignore-missing-imports
python plugins/m1frame/tests/check_mcp.py
python plugins/m1frame/tests/check_upgrade.py
python -m scripts.doctor --config PATH_TO_RUNTIME/config.yaml --live --output module-audit.json
```

The doctor uses isolated fixtures for optional modules. `--live` permits a small real provider request. It reports missing setup separately from verified execution. Use the configured runtime interpreter to test its installed optional packages.

## Remaining actions

1. Resolve the existing OpenRouter 403 with the provider/account or network administrator, then rerun a full workflow. Do not infer readiness from key presence alone.
2. Configure Exa/Voyage credentials locally to test authenticated enrichment. Do not put credentials into Git or chat.
3. Restore a local inference service and provision the intended classifier before enabling ShieldGemma. LM Studio's daemon timed out in this audit.
4. Reconnect the existing Codex MCP session to activate the corrected project launch configuration. A fresh subprocess was verified against the managed runtime.
5. Select individual scientific workflows and validate their data/dependencies before relying on them. The catalog is not an execution certification.

Evidence is retained locally in `workspace/qa-audit/`: release-core.txt, release-regressions.txt, release-lint.txt, release-types.txt, plugin-check.txt, upgrade-check.txt, doctor.json, provider-recheck.txt, managed-context-final.txt and runtime-deployment.json. No credential contents are included in this report.
