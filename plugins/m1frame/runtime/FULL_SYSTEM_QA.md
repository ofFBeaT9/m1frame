# Full-system prompt routing QA — v1.10.0

Final review: 2026-09-30. The earlier audit is in `EFFICIENCY_REVIEW.md`.

## What a prompt reaches

| Entry point | Behavior |
| --- | --- |
| Studio Chat, Full M1Frame (default) | Recent conversation enters a recorded workflow: learned-skill recall, scientific discovery, wiki recall, BMAD planning, council brainstorm, role agents with registered tools, synthesis, council/red-team review, optional structural sensor, skill learning/optimization, and wiki ingestion. Investigation runs when an investigator story is planned. |
| Studio Chat, Quick answer | Explicitly bypasses the workflow; streaming conversation with wiki grounding, or offline keyword lookup. |
| Coding assistant in this repository | `AGENTS.md` directs task-level capability discovery, relevant wiki/skill reading, host Miras recall when connected, actual execution and QA. `CLAUDE.md` references the same instructions. Host compliance and available host tools remain separate from Python runtime configuration. |
| CLI and MCP workflow | Same pipeline and final checked output. MCP also exposes `m1frame_context` for discovery. |

Discover availability with `python -m scripts.context_probe --query "your task"`,
`GET /capabilities?q=your-task`, or `m1frame_context`. Full exposure means relevant
capabilities are discoverable and usable, not that every skill and agent runs for
every prompt. Tool calls are bounded to four per story by default and do not grant
write approval. The runtime has no general-purpose shell tool.

## Installed and connected in this checkout

- 53 registered tools, including learned-skill discovery and reading.
- 163 scientific skill entries installed at pinned revision
  `9cf7d9aea7d84754db4c167ab04b299d33c444bc`.
- Static scientific audit: no catalog errors; 540 Python resources parse with
  zero syntax errors. Optional packages, credentials and experiments are not certified.
- Catalog installation lives in ignored `.external/scientific-skills`. It is local
  setup, not vendored into the commit. Fresh clones need `python -m scientific install`.
- Host Miras recall worked during this review. Python does not automatically connect
  that external memory service; it recalls the local wiki and learned recipes.
- External Headroom is not connected. The local request guard enforces a character
  cap and, when configured, a conservative UTF-8-byte token estimate plus output reserve.
  Set backend `context_window_tokens` or `context.model_windows` from the actual
  deployed model. An unknown window is reported as unknown, never guessed. Claude
  CLI output size remains provider-controlled; its reserve is only an estimate.

## Validation

Run these from the repository root:

```
python scripts/qa_validate.py
python -m unittest scripts.test_scientific scripts.test_efficiency scripts.test_full_system
ruff check .
mypy agents/ llm_client.py --ignore-missing-imports
```

Coverage includes all 164 existing checks, 8 scientific checks, 14 efficiency
regressions, and 17 full-system regressions. The latter exercise default full-chat
routing, complete final responses, history, explicit failures, real calculator
execution, unapproved-write denial, tool budgets, skill discovery, scientific
context accounting, request headroom, .env loading and CLI isolation.

`scripts/test_studio_ui.cjs` runs against a local API with Playwright installed.
It uses mocked model responses to check default full mode, quick opt-in,
conversation continuity, HTTP error display and the mobile Send button. It does
not consume paid model calls. Run it with `M1_TEST_URL` if the API is not at
`http://127.0.0.1:8089`; install/provide Playwright separately for this optional UI test.

## Live limitation and activation

The configured backend is still `claude`; this checkout had no Anthropic API
credential at verification time. A minimal live request using the installed Claude
CLI was attempted and failed with **OAuth access token expired**, despite its
status command reporting a logged-in account. No successful live workflow or
live answer-quality benchmark is claimed.

For API mode, configure the credential in the environment or local `.env`. For
CLI mode, re-authenticate with `claude auth login` and select `claudecli` in Studio
Settings/config.yaml. Ensure the configured model is available to that account.
Then submit a small full-chat prompt and inspect its recorded run. Keep authentication
material out of Git and chat messages.

Full chat requires a working model; it intentionally reports a setup error when
none is configured. Quick answer remains available for offline wiki lookup.

Repository instruction discovery follows the official
[AGENTS.md guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
Instructions make capabilities discoverable; they do not install host MCP services
or change the model's intrinsic capability.
