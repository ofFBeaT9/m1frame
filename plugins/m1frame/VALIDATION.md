# Preview validation — 2026-10-01

## Passed

- Windows / Python 3.13: 164 upstream offline QA checks and 61 regression tests.
- Upstream Ruff checks and mypy checks (18 source files).
- Plugin manifest and skill validation; wrapper lint.
- Actual MCP startup, nine-tool discovery and boolean effect annotations.
- Context, tool/skill listing, grounded retrieval and calculator.
- Unapproved file write denied; approved test write succeeded; traversal rejected.
- Unknown tool and missing model credentials returned honest errors.
- Optimizer score did not decrease; optional sensor path returned bounded results.
- Studio health/startup/reuse and invalid-port checks.
- Studio rendered in the Codex browser; recorded demo completed in run history; wiki and graph displayed.
- Restart preserved runtime data.
- Isolated dependency installation from declared requirements.

## Limits

- Live provider workflow: not verified. Claude login authenticated but tiny requests did not return. A US$0.02 per-request CLI cap was supplied; no successful response or final cost was reported. The publisher elected to defer live testing.
- Rust Sentrux: not installed on the test machine. The separate Python package was detected and exercised; no successful Rust measurement is claimed.
- Windows and Linux: plugin protocol CI passed for the preview. macOS was not tested.
- A new Codex chat is needed to pick up installed tools. Direct protocol tests are distinct from host conversational routing.
- No hosted service or universal-directory review/publication.

## Packaging

Runtime source: fbb06dd5cb066d26627e3dc88868312016cebdbe, unmodified. Wrapper fixes are outside runtime/. Archives include manifests, skill, artwork, license, setup, tests and source. No .env files, virtual environments, Git metadata, local logs or test data are packaged.
