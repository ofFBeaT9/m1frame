# Operational audit repairs — October 5, 2026

This change repairs approval/output handling, wiki persistence contracts, optional
integration reliability and deployment consistency. It does not certify every live
provider, external service or scientific workload.

## Changes

- Withhold rejected drafts; expose authoritative approval, storage and learning
  status with durable execution receipts. Record actual tool observations and
  provider usage when available, without recording model reasoning.
- Use final-answer prompts and sanitize malformed/repeated reasoning blocks.
  Check buffered streamed output before delivery, and validate final output
  before learning or optimization can persist it.
- Review the candidate independently in the council red team. Preserve the
  candidate that passed review instead of returning an unchecked rewrite.
- Enforce two-pass wiki ingestion with immutable raw capture for named and
  unnamed input, source evidence, runtime dates, synthesis/project metadata,
  index updates and deterministic maintenance. Resolve configured wiki/purpose
  paths consistently across workflow and Studio.
- Preserve evidence when entity records merge, respect investigation output
  directories, avoid output collisions and expose integration failures.
- Bound provider retries/timeouts; report access and quota errors explicitly.
  Optional classifier failures remain closed, and default compression does not
  silently download an ML model or compress system instructions.
- Discover paginated MCP tool inventories with repeated-cursor protection.
- Save API completion state before emitting the terminal stream event.
- Synchronize the bundled plugin runtime with source and enforce consistency in
  CI. Plugin source manifests advance to 0.1.3; publishing a release is separate.

## Verification of this branch

- 164/164 core offline checks passed.
- 100 regression tests: 99 passed, one expected optional-dependency skip.
- Repository-wide Ruff passed; mypy passed on 19 source files.
- Studio browser regression passed: full/quick modes, history, error display,
  mobile layout and graph tooltip escaping, using controlled responses.
- Fresh plugin protocol/lifecycle checks passed: inventory, real local tools,
  approval boundaries, persistence and Studio start/stop.
- Upgrade backup and credential/configuration/history preservation test passed.

These are local Windows results. Remote CI results must be checked separately
after a push; prior release CI does not certify this commit.

## Remaining live limits

A live run passed council review at 9/10 before encountering invalid generated
wiki metadata. That defect now has a runtime fix and regression coverage. Final
approved live ingestion and retrieval remain unverified because the configured
OpenRouter free account has exhausted its daily allowance. Two newly supplied
keys were valid but both reported zero remaining free requests. No paid fallback
or key rotation to evade limits was introduced.

Historical private-wiki source recovery remains incomplete and low-confidence
references stay flagged. Exa/Voyage credentials, a running optional classifier,
and domain-specific scientific dependencies require separate local setup.

The full workflow is explicitly invoked; ordinary host prompts and quick utility
calls do not automatically traverse every layer. Optional layers are conditional.
Local Headroom/SkillOpt/Sentrux fixture results do not establish live token savings,
general reasoning improvement, or factual correctness.

## Repeat the checks

```sh
python scripts/qa_validate.py
python -m unittest discover -s scripts -p "test_*.py"
ruff check .
mypy agents/ llm_client.py --ignore-missing-imports
python plugins/m1frame/scripts/sync_runtime.py --check
python plugins/m1frame/tests/check_mcp.py
python plugins/m1frame/tests/check_upgrade.py
```

For existing plugin installations, use the explicit runtime upgrade command
documented in the plugin README, then reconnect the plugin. Upgrades preserve
local provider settings, credentials, wiki content and history.
