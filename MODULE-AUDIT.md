# m1frame module audit — 2026-10-02

This is a repair and verification report, not a claim that every possible workflow works or that m1frame is AGI. A real self-audit completed with apodex/apodex-1.1-mini:free: 28 model calls, total reported cost $0, and all core stages executed. The council rejected the generated answer at 3/10. Completion of execution is not proof of answer quality. This live run exposed further tool-budget and rejected-knowledge bugs, repaired with regression tests. Keys are kept outside the repository.

## Reproduced and repaired

- Studio silently selected demo when a provider was missing. Live is now the default and missing setup returns a visible 503; demo requires an explicit choice.
- Studio retained stale live-readiness after provider changes and failed to check save/run HTTP errors. Both paths now refresh or report failure.
- Mode toggling removed the CSS class needed to find the Demo button. Repeated Live/Demo switching is now browser-tested.
- Provider model validation rejected OpenRouter `:free` identifiers. Valid identifiers are accepted and quoted safely when saved; model-only edits persist. Invalid patches do not partially switch providers.
- Newly added local credentials were invisible until restart. Readiness now reloads missing environment values from the local .env.
- The external MCP connector was an unconditional NotImplementedError. It now manages a real subprocess session, discovery, calls, timeouts and cleanup; registered remote tools retain approval requirements.
- Rust Sentrux scan used CLI check, which requires a rules file. It now uses the real MCP scan tool for read-only measurement and detects a local official binary.
- Investigation advertised conceptual tools but made only one model call. It now executes the bounded registered tool loop and identifies itself as m1frame's implementation, not an invoked upstream OpenPlanter engine.
- Malformed wiki contradiction output incorrectly produced a clean verdict. Invalid responses now fail explicitly without recording a clean result.
- Skill optimization's fixed candidate vocabulary could not cover arbitrary requested keywords. Candidates now include the requested vocabulary. This is still a simple lexical objective, not proof of semantic improvement.
- Plugin updates left persistent runtime code unchanged. An explicit, tested runtime updater backs up changed code and preserves keys, settings and user data.

Additional live-test repairs:

- Tool agents now see their remaining call budget and a final-answer instruction when it is exhausted; underlying story failures are visible.
- Rejected/blocked output is not ingested into the wiki. Rejected output is visibly labeled; Studio records needs_review.
- Explicit OpenRouter free_only mode rejects paid model IDs and caps provider prices at zero. Provider calls have bounded timeouts.
- Reasoning-only responses are not substituted for final answers.
- Semantic wiki lookup handles heading-only pages and hyphenated filenames; embeddings are cached within a wiki instance and index writes update existing IDs.

## Evidence by module

| Module | Evidence | Remaining limit |
|---|---|---|
| BMAD, council, local Miras, Karpathy, wiki pipeline | Core offline suite plus a real 28-call self-audit covering every core stage | Free model generated a poor answer; council rejected it at 3/10 |
| Investigation | Real read_file and other tool observations during live self-audit; calculator fixture also tested | Exa and Voyage require their own credentials |
| Guardrails | Rule-based input/output, injection and approval regressions | Optional ShieldGemma classifier needs a running model endpoint |
| Tools | Built-in core suite, path boundaries and approval checks | No claim of every possible input being safe or correct |
| External MCP client | Real FastMCP subprocess round trip, approval denial/approval, cleanup | Explicit server connection required; host connections aren't inherited |
| Sentrux | Official Windows Rust v0.5.7, real MCP discovery and scan | Agent-directory measurement 6433/10000: CONCERNS, advisory; not a model quality score |
| SkillOpt | Real 0.2.0 apply_patch engine; measured lexical score -0.06 to 1.92 | Text may lose meaning while improving the simple objective; review suggestions |
| Headroom | Real 0.39.1 compression: repetitive fixture 1631 to 43 tokens, protected system/current user retained | Representative sample only; not proof every compressed conversation retains meaning |
| Scientific library | 163 pinned skills installed; discovery/read exercised; 540 Python resources parsed without syntax errors | Static audit only; libraries, datasets, services and hardware needed by individual skills are not all installed/tested |
| ADHD formatter | Opt-in formatting and structured-output preservation tests | Local response-shaping implementation |
| Scheduler, metrics, events, gateways | Offline scheduler, event-stream, persistence and gateway regressions | External delivery accounts/endpoints not configured for live tests |
| Host Miras memory | Actual host recall used during this audit | Separate from Python runtime's Miras orchestrator |
| Semantic wiki | Real all-MiniLM-L6-v2 embeddings, LanceDB, 17 source pages indexed, resolved retrieval and duplicate prevention | Optional dependencies installed locally; no claim about retrieval quality across all corpora |

## Reproduce

```sh
python scripts/qa_validate.py
python -m unittest scripts.test_live_configuration scripts.test_mcp_connector scripts.test_full_system scripts.test_integrations scripts.test_scientific scripts.test_efficiency scripts.test_redteam
python plugins/m1frame/tests/check_upgrade.py
python plugins/m1frame/tests/check_mcp.py
ruff check .
mypy agents/ llm_client.py --ignore-missing-imports
```

The browser regression `scripts/test_studio_ui.cjs` checks live/demo toggles, provider-readiness updates, full chat default, explicit quick mode, history, error display, mobile layout and graph text handling. Provider responses in browser tests are fixtures, not live-model evidence.

## Prompt routing

Studio Chat defaults to the complete local workflow. The selected plugin's skill instructs Codex to run the full workflow for substantive m1frame requests. A plugin cannot transparently intercept every unrelated Codex prompt. Optional integrations run where applicable; forcing every scientific skill or network tool into every prompt would not be a valid functional test.

## Still needed

OpenRouter live execution is now verified with a user-provided key, an explicit :free model and zero-price provider routing. The first model returned a shared-provider 429; a different free model worked. Do not commit credentials. Further task-quality evaluation is still needed; the completed audit report failed its council gate. Exa, Voyage, ShieldGemma and external messaging services require their own explicit configuration. Original upstream frameworks are not automatically installed or invoked merely because their patterns are implemented here.
