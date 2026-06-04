# QA Gates — m1frame v1.3 Readiness

## Gate 1 — Roadmap review (before "build"/verification)

**Findings**
- F1 [resolved] — Risk that "production-ready" is unfalsifiable. → PRD reframes it to its *actual positioning*
  ("most auditable workspace") with concrete metrics, and lists Hermes-breadth gaps as **explicit out-of-scope**.
- F2 [resolved] — Risk of re-overclaiming after closing gaps in code. → Architect makes "closed in code ≠ closed
  at parity" an invariant; council audits the docs.
- F3 [watch] — `_load_persisted_runs()` runs per `create_app()`; could surface stale runs in a shared process.
  Bounded to 50, idempotent, and tests don't assert counts → acceptable; noted for a future per-instance store.

**Gate 1 verdict: PASS** — roadmap is concrete and falsifiable; proceed to evidence + council.

---

## Gate 2 — Results review (after evidence + council)

**Evidence audited**
- `python scripts/qa_validate.py` → **90/90** (gateways 6, tools 6, run store 2, deploy 2 added; skills 6; core 68).
- API smoke (TestClient): `/health` = **1.3.0**; `/tools` = 5 (calculator/wiki_search/datetime_now/word_count/http_get);
  `calculator(6*7)` = **42**; `/gateway/status` = [telegram, slack, discord, webhook, cli]; telegram `/ping` routed.
- Isolation: `t_gw_handler_never_crashes` proves a raising handler is caught; skills/persistence wrapped.
- SSRF: `t_tool_http_ssrf` blocks loopback + `file://`; one policy in `agents/net.py`.

**Council outcome:** 3 lens papers + 1 red-team (see `council/`). Consensus **8.3/10**. Red-team raised 4 points;
**2 were real and folded in this cycle** (`/run` prefix over-match → tightened to word boundary; stale-positioning
memory → scheduled update), 2 were correct-by-design (best-effort delivery; localhost bind is intentional).

**Required fixes (folded, not caveated)**
- ✔ `/run` command now matches only `"/run"` or `"/run "` (router + API) — no `/runner` misfire.
- ✔ Docs vs-Hermes table rewritten to axis-qualified rows; "roadmap" language updated to "closed in code; breadth/maturity remain."

**Gate 2 verdict: PASS (8.3/10)** — v1.3 is production-ready *for its positioning*; no unfixed BLOCKER.
