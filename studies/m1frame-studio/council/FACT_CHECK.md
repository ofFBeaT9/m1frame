# Council Fact-Check — m1frame Studio (BMAD Cycle B)

Three specialist council members audited the build and the competitive claims **in parallel**, each reading the
real code. Verdicts: **conditional / conditional / conditional** (scores 6 / 6 / 6). Their papers are below,
followed by the synthesis + my triage (the orchestrator acting as first-pass red-team: *verify before folding*).

---

## 1 · Competitive / Parity member — VERDICT conditional · SCORE 6/10

- **[BLOCKER]** "independent red-team that overrides the council" is **not in `agents/council.py`** — `DEFAULT_PERSONAS`
  is only Critic/Advocate/Domain Expert. The red-team exists in the demo fixture + UI render slot, and in the
  `/m1frame` *methodology* (which spawns a red-team), but not in the council class. → **Build it or retract it.**
- **[MAJOR]** Parity row 1 "far ahead" hinges on that red-team; downgrade unless it's real in code.
- **[MAJOR]** Any unqualified "far superior" must be axis-qualified (the ROADMAP's own Analyst conclusion already says so).
- **[MAJOR]** Backend flexibility: note "single model per backend" vs Hermes' 200+ registry.
- **[MINOR]** `_RUNS` is in-memory → replay is "within a session"; qualify it.
- **[MINOR]** OpenPlanter's 19-tool suite needs the optional install; note the default is LLM-only mode.
- **Honest headline proposed:** *"the most transparent multi-agent workspace there is."*

## 2 · Frontend / UX member — VERDICT conditional · SCORE 6/10

- **[BLOCKER]** Nav/brand/chip/palette are click-`<div>`s → **no keyboard access, no a11y names.** Make them `<button>`.
- **[BLOCKER]** No `prefers-reduced-motion` guard (starfield rAF, aurora, breathe/pulse/blink, card rise).
- **[BLOCKER]** `--mute` (#6b7793 ≈3.4:1) and `--faint` (#454f66 ≈2.0:1) **fail WCAG AA** on the dark bg.
- **[MAJOR]** `runbtn` can read stuck-disabled if you navigate away mid-run (stale closure ref + `S.busy`).
- **[MAJOR]** score-ring conic-gradient "always near-empty." → **TRIAGE: INVALID** (reviewer mis-did the math;
  `--p = score*10`, so 8 → 288°. Verified correct; no change.)
- **[MAJOR]** No `:focus-visible` rings.
- **[MINOR]** LIVE toggle gives only a transient toast when no key → disable the LIVE button + tooltip.
- **[MINOR]** `md()` link regex could emit `javascript:` hrefs → sanitize.

## 3 · Backend / Streaming / Security member — VERDICT conditional · SCORE 6/10

- **[BLOCKER]** `_run_live` happy path never calls `bus.close()` → "SSE hangs." → **TRIAGE: NOT a hang**
  (`run_workflow` emits a terminal `done`); but add a defensive idempotent `bus.close()` anyway.
- **[BLOCKER]** `_replay_demo` happy path missing `done` → "hangs." → **TRIAGE: NOT a hang** (the fixture's last
  event is `done`); add defensive `bus.close()` anyway.
- **[MAJOR]** `EventBus.close()` checks `closed` outside the lock → duplicate `done` possible. → **VALID, fix.**
- **[MAJOR]** `_RUNS` + `bus.history` grow unbounded. → **VALID, cap it.**
- **[MAJOR]** `PATCH /config` writes `config.yaml` unauthenticated; `model` unsanitized → YAML injection. → **VALID.**
- **[MAJOR]** `webhook_url` SSRF (e.g. cloud metadata). → **VALID, validate scheme + block internal.**
- **[MINOR]** Default bind `0.0.0.0` makes the above network-reachable → bind `127.0.0.1`.
- **[MINOR]** chat producer thread leaks on client disconnect → stop-flag.
- Confirms the **"additive / non-breaking" claim holds** (`emit=None` no-op; council callbacks default `None`).

---

## Synthesis — what gets folded in (fix, don't caveat)

**Made real in code (the important one):** a genuine **Red-Team reviewer in `agents/council.py`** that runs after
the 3 personas and can **veto** a pass — so "an independent red-team that overrides the council" is true in the
*engine*, not just the demo. (Convergence: all three members + the methodology already treat the red-team as core.)

**Backend:** lock-guarded idempotent `EventBus.close()` (no duplicate `done`); defensive `bus.close()` on both run
paths; `_RUNS` capped + bus released on terminal; `model` validated before `config.yaml` write; default bind
`127.0.0.1`; webhook scheme/host validation; chat stop-flag on disconnect.

**Frontend:** real `<button>` semantics + `aria-label`/`aria-current`/`aria-expanded`; a `prefers-reduced-motion`
block (animations off, star loop + graph physics paused); WCAG-AA contrast (`--mute`/`--faint` raised);
`:focus-visible` rings; resilient run-button state; LIVE disabled w/ tooltip when key-less; `md()` href sanitizer.

**Docs:** axis-qualified headline shipped; replay qualified "within a session"; OpenPlanter tool caveat;
parity row 1 kept "far ahead" **because the red-team is now real in code**.

**Rejected (verified false):** the two "SSE hangs" blockers and the score-ring blocker.

A second adversarial **red-team pass** (`RED_TEAM.md`) attacks this synthesis after the fixes land.
