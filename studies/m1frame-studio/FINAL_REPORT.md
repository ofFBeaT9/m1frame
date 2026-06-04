# m1frame Studio — Final Report

**Question:** make m1frame decisively better than Hermes Agent, using the m1frame team (miras + BMAD + council),
with the most beautiful, easy-to-use UI.
**Status:** delivered + hardened across **two BMAD cycles** with a **3-member council + red-team** fact-check.
All blocker/major findings folded in (fix, don't caveat). **68/68 QA green · wiki lint 0/0 · zero console/server
errors.**

---

## The verdict (one honest paragraph)

We cannot truthfully claim m1frame is "10000× better" or broadly superior to Hermes Agent — Hermes leads on
multi-platform gateways, 40+ tools/MCP, 200+ models, a self-improving skill loop, six deploy backends, and
~10k-commit maturity. **What we built instead is a decisive lead on the one axis that determines trust:**
**m1frame Studio is the most *auditable* multi-agent workspace there is.** It is the only one that lets you
*watch* a council deliberate persona-by-persona, *watch* an independent red-team veto an overconfident pass,
*click* the grounding in a live knowledge graph, and *see* memory accumulate — all zero-build, offline, and
zero-lock-in. That is a real, defensible, differentiated win, and it is exactly what Hermes (a single
self-improving agent) structurally cannot show.

## What shipped

- **`m1frame-studio.html`** — one zero-build, offline, hand-built ("deep observatory") file. Six surfaces:
  **Studio** (live 7-pillar deliberation), **Chat** (grounded + cited), **Graph** (knowledge constellation),
  **Runs** (replayable traces), **Wiki** (reader), **Settings** (one-click backend switch · scheduler · metrics).
- **Streaming engine** — `agents/events.py` `EventBus` + `api/server.py` SSE (`/run/{id}/events`, `/chat`,
  `/wiki/graph`, `/memories`, `/metrics.json`, `GET|PATCH /config`). Pipeline instrumented additively
  (`emit=None` no-op) — the CLI and 68/68 QA suite are byte-for-byte unaffected.
- **Real red-team in code** — `agents/council.py::review()` now runs an independent adversary that can **veto a
  pass**. The headline differentiator is true in the engine, not just the demo.
- **Three tiers** — live (FastAPI + key) · server-replay (no key) · pure-static (no pip). The bundled demo
  replays the *real* [[Chip Manufacturing Decision]] deliberation with **zero API key**.

## How the team was used

- **miras** — recalled prior context first; stored 3 reusable decisions/lessons; exported the snapshot (61 memories) that the Studio's memory feed reads.
- **BMAD ×2** — Cycle A (ship the Studio) and Cycle B (surpass-Hermes hardening), each with an Analyst→PM→Architect→SM plan and a heavy QA gate (`ROADMAP.md`, `QA_GATE.md`).
- **Council (3) + Red-Team (1)** — spawned real agents to fact-check the build *and* the claims (`council/FACT_CHECK.md`, `council/RED_TEAM.md`). Verdicts conditional → all findings folded in.
- **LLM-wiki** — two-step ingest of `[[m1frame]]` + `[[m1frame Studio]]`; index + log updated; lint 0 errors / 0 orphans.

## What the council + red-team changed (evidence the process worked)

- **Made the red-team real** (was a vaporware claim) · **security**: SSRF guard, config-write validation,
  localhost bind, idempotent event close, run-store cap · **accessibility**: real `<button>`s, reduced-motion
  (incl. graph physics, caught by the red-team), WCAG-AA contrast, focus rings, markdown href sanitizer ·
  **honesty**: axis-qualified every comparative claim.
- **Verify-before-fold caught 3 false "blockers"** (two "SSE hangs", one score-ring) — rejected with proof.

## Verification

`python scripts/qa_validate.py` → **68/68** · `python wiki/lint.py` → **0 errors / 0 orphans** ·
`node --check` on the UI script → clean · security guards unit-checked (`_safe_webhook`, `_MODEL_RE`) ·
driven in a real browser across all six surfaces (full demo run, council debate, graph growth, chat, replay) —
**zero console + zero server errors**.

## Next (honest roadmap to close the Hermes gaps)

1. One webhook→Telegram gateway bridge (start of multi-platform). 2. Skill-learning loop (persist successful
story chains as miras patterns). 3. MCP tool surface. 4. Model-registry UI. 5. Persistent run store (replay
across restarts). Each additive, like the Studio was.
