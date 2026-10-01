# M1Frame 1.10.1 red-team QA

Date: 2026-09-30. Scope: repository runtime, Studio/API, orchestration, tool
boundaries, persistence, optional modules, packaging and declared dependencies.
Upstream main through 6cd4479 is preserved. Claude authentication, user settings
and live-provider configuration were not changed during this audit.

## Findings repaired

| Area | Failure | Repair |
| --- | --- | --- |
| API | Cross-origin unauthenticated workspace operations | Same-origin checks; local host and peer validation; token authentication for remote clients; request and active-run bounds |
| Studio graph | Wiki titles rendered as HTML in tooltips | Construct text nodes instead of injecting HTML |
| Static servers | Entire repository could be served | Explicit asset allowlist, no directory listing, no symlink escape |
| Fetch/webhooks | Redirect and DNS bypass of literal-IP checks | Resolve once, reject non-public answers, pin connection address, preserve TLS hostname verification, no redirects, bounded reads |
| File tools | Hidden credentials and recursive-search escape | Protected paths including Windows streams; validate each discovered file; bounded reads |
| Computation tools | Base 1 loops forever; exponent and regex denial of service | Validated bases and numeric limits, bounded allocations, regex timeouts |
| Council | Hard-coded passing score; inconclusive red-team accepted | Configured threshold enforced; invalid scores fail; red-team checks approved candidate and must explicitly pass |
| Headroom | Mutating failed compressor can damage original messages | Deep-copy isolation; preserve system instructions and latest user request; reject expanded/invalid output |
| Scheduler | Path traversal; invalid timers; duplicate start/rearm after stop | Validate jobs; guard timer lifecycle; shared API scheduler with startup/shutdown and lazy provider creation |
| Skills/wiki | Concurrent writes lost; raw source overwrites | Locked skill mutations, unique temporary files, append-only wiki logs/index, exclusive source/page creation |
| Saved runs | Event stream dereferenced an absent bus | Replay saved events and terminate explicitly |
| Packaging | Flat-layout discovery and module entry point missing | Explicit package discovery and m1frame.__main__ |
| Remote tool adapter | Imported tools bypassed approval | Require explicit approval for remote registered tools |
| Dependencies | Vulnerable dotenv pin; OpenAI/httpx constructor crash; removed MCP 2.x FastMCP import | Patched dotenv, compatible OpenAI minimum, MCP <2 |

The dotenv finding is [GHSA-mf9w-mj56-hr94](https://github.com/theskumar/python-dotenv/security/advisories/GHSA-mf9w-mj56-hr94).
The affected write helpers are not used by M1Frame, but the vulnerable requirement
was replaced. The audit tool returned duplicate records for that one advisory.

## Verification

- `python scripts/qa_validate.py`: 164/164 offline mock checks.
- `python -m unittest scripts.test_scientific scripts.test_efficiency scripts.test_full_system scripts.test_integrations scripts.test_redteam`: 61 passed, including 18 new adversarial regression methods.
- `ruff check .`: clean.
- `mypy agents/ llm_client.py --ignore-missing-imports`: 18 source files, no errors.
- Studio browser smoke: full workflow default, explicit quick mode, history, HTTP error display, mobile layout, graph tooltip XSS defense; no page errors. Provider responses are mocked.
- Capability discovery: 54 registered tools, 12 roles, 163 locally installed scientific skills, no catalog errors. Optional external Headroom is disabled.
- Clean requirements target: all 225 tests pass after the SDK compatibility fixes; provider client construction uses dummy credentials without requests, and MCP imports successfully.
- Versioned wheel builds; isolated installed `python -m m1frame --help` succeeds.
- `pip-audit -r requirements.txt`: no known vulnerabilities after updating the dotenv requirement. This checks advisories for resolved dependencies, not every optional package or future resolution.

The tests use real filesystem, threading, local HTTP and browser behavior where
applicable. External network boundaries use controlled DNS/socket mocks; no scans
were sent to private services or unrelated hosts. No live-provider intelligence,
paid requests, GPU workloads, external Headroom installation or hardware behavior
was verified. Optional scientific dependencies were not installed wholesale.

## Deployment changes and remaining limits

Docker now requires `M1FRAME_API_TOKEN` and publishes only on loopback. Browser
Basic login uses the token as password; API clients use Bearer authentication.
Gateway proxies must supply authentication too. MCP HTTP is loopback-only and
requires an authenticated proxy for remote use. See SECURITY.md.

This is a single-owner, single-process service, not a multi-tenant sandbox.
Custom plugins execute trusted Python; file guards do not detect secrets placed
in ordinary documents or defeat a hostile local filesystem actor. The stdio MCP
client connector remains explicitly unimplemented; host MCP connections are
separate. A local Headroom budget is an estimate unless the actual model window
is configured. Full Studio routing does not force every skill or agent to execute
on every prompt: discovery is broad and retrieval is selective.

Passing these checks is evidence for the covered cases, not proof that no bugs
remain. Live-provider and optional-hardware checks require their own environments.
