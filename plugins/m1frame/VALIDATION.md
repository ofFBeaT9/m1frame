# Validation — source 0.1.3

October 5, 2026: 164 core checks; 99 regression passes and one skip; Ruff, mypy, browser, plugin protocol/lifecycle and upgrade preservation checks passed locally on Windows. Final approved live wiki roundtrip remains quota-blocked. No remote CI or published release is claimed for this source version. See [audit repairs](../../AUDIT_REPAIRS.md).

## Historical 0.1.2 evidence

# Validation â€” preview 0.1.2

Verified locally on Windows, 2026-10-02:

- 164 core offline QA checks.
- 74 regression tests, including real subprocess MCP communication, approval enforcement, provider-setting persistence and investigator tools.
- Runtime-upgrade backup/data-preservation test.
- Real plugin protocol checks from fresh state: all nine tools, annotations, approvals, path boundaries, Studio lifecycle and persistence.
- Browser tests: live/demo switching, provider updates, full chat, explicit quick mode, history, errors and mobile layout.
- Ruff and mypy (18 source files).
- Actual installed Headroom compression, SkillOpt editing and official Rust Sentrux measurement.
- Scientific catalog: 163 skills, 540 Python resources syntax-checked; discovery and reading exercised.

A real full self-audit made 28 OpenRouter free-model calls with total reported cost $0. All core stages executed. The council rejected the generated report at 3/10. That run exposed further bugs, now repaired: tool agents see their call budget, and rejected answers are labeled and excluded from wiki ingestion. A completed pipeline is not proof that its answer is correct. Optional service/hardware workflows are not all verified. See MODULE-AUDIT.md for the detailed evidence and limitations.

The GitHub workflow repeats offline/runtime/plugin checks on Windows and Ubuntu. See the release's commit checks for their actual status.

Real semantic wiki retrieval passed with all-MiniLM-L6-v2 and LanceDB, including existing-page lookup and duplicate prevention.
