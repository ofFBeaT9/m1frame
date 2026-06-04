# m1frame Studio — QA Gates

Two heavy QA gates, one per BMAD cycle. Principle: **fix, don't caveat.**

---

## Gate A — Studio build (Cycle A)

**Reviewed:** the streaming engine, the six-surface UI, and the demo/replay tiers.

| Check | Result |
|---|---|
| 68/68 offline QA suite (`scripts/qa_validate.py`) | **PASS** — unchanged; instrumentation is `emit=None` no-op |
| JS parses clean (`node --check`) | **PASS** (after fixing a missing `)` in the accent-dots block) |
| All six surfaces render + drive in a real browser | **PASS** — Studio, Chat, Graph, Runs, Wiki, Settings |
| Full demo run streams end-to-end | **PASS** — 97 events incl. council debate, graph deltas, final |
| Console / server errors | **PASS** — zero |

**Findings folded in (not caveated):**
- **Layout height-chain bug** — `.view` wasn't the scroll container (whole document scrolled); the header could
  scroll away. → Added `min-height:0` to the flex/grid chain + `height:100vh; overflow:hidden` on `#app`. Verified.
- **Graph link double-count** — `applyGraphDelta` re-pushed links each run (53 → 106). → Deduped by sorted
  source/target key. Verified back to 53.

**Gate A verdict: PASS.**

---

## Gate B — Council + Red-Team fact-check (Cycle B)

**Method:** 3 specialist council members in parallel (parity, UX, backend/security) + 1 independent red-team
attacking the post-fix synthesis. Papers in `council/FACT_CHECK.md` and `council/RED_TEAM.md`.

### Council findings folded in
**Made real in code (the headline fix):** an **independent Red-Team** now runs in `agents/council.py::review()`
and can **veto a pass** (`verdict=fail`). The differentiator is true in the *engine*, not just the demo/UI.

- **Backend/security:** lock-guarded idempotent `EventBus.close()` (no duplicate `done`); defensive `bus.close()`
  on both run paths; `_RUNS` capped at 200; `PATCH /config` `model` validated (`_MODEL_RE`, no `:`/spaces);
  default bind `127.0.0.1`; webhook SSRF guard; chat producer stop-flag on disconnect.
- **Frontend/a11y:** nav/brand/chip → real `<button>`s with `aria-label`/`aria-current`/`aria-expanded`;
  `prefers-reduced-motion` honored (CSS animations off, **starfield + graph physics frozen**); WCAG-AA contrast
  (`--mute`/`--faint` raised); `:focus-visible` rings; resilient run-button; LIVE disabled w/ tooltip when key-less;
  markdown `href` sanitizer (blocks `javascript:`).
- **Docs:** axis-qualified "most auditable" headline; replay "within a session"; OpenPlanter tool caveat.

### Red-team residuals (caught what the council missed) — folded in
- **Graph physics ignored reduced-motion** (synthesis overclaimed "paused"). → **Fixed** (settle-then-freeze).
- **`_safe_webhook` allowed loopback/private IPs.** → **Fixed** (block private/loopback/link-local/reserved).
- **`_MODEL_RE` allowed `:`.** → **Fixed.**
- Heading "beats a single-shot agent" overreach + veto-scope rhetoric → **Fixed (docs)**.

### Rejected after verification (council/red-team errors caught by the orchestrator)
- "SSE hangs on success" (×2): **false** — `run_workflow` and the demo fixture both emit a terminal `done`
  (defensive `bus.close()` added anyway).
- Score-ring "always near-empty": **false** — `--p = score*10` ⇒ 8/10 → 288°. Correct as built.
- `_new_run` "race": **false** — single asyncio loop + no `await` ⇒ atomic.

### Re-verification (post-fix)
| Check | Result |
|---|---|
| 68/68 QA suite (incl. real red-team in council) | **PASS** |
| JS parses clean | **PASS** |
| Browser: a11y (real buttons, LIVE disabled, contrast) + full run | **PASS**, zero console/server errors |

**Gate B verdict: PASS** (all blocker + major findings from both the council and the red-team folded in).
