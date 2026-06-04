# m1frame Studio — BMAD Roadmap (two cycles)

> Method: two BMAD cycles (Analyst → PM → Architect → Scrum Master), each closed by a heavy QA gate, then a
> spawned 3-member **Council** + **red-team** fact-check (see `council/`). Grounded in miras memory, the live
> repo, and the Hermes-Agent feature set. Goal: *credibly* beat Nous Research's Hermes Agent on m1frame's
> unique strengths — not by slogan.

---

## CYCLE A — Ship m1frame Studio

### A1 · Analyst — Project Brief
**Problem.** m1frame had a strong epistemic engine (BMAD + Council + red-team + LLM-wiki + miras) but exposed
it only as a *blocking CLI that prints to stdout* and two *static* HTML reports. The reasoning — the thing that
makes m1frame trustworthy — was invisible. Meanwhile Hermes Agent ships a polished TUI, gateways, and a
self-improving loop.
**Core hypothesis.** The highest-leverage, defensible move is to make m1frame's deliberation **visible, live,
and beautiful**. Hermes *acts*; m1frame *deliberates, grounds, and remembers* — and can now *show* it.
**Grounded anchors.** 7-pillar pipeline in `scripts/run_workflow.py`; Miras already exposes
`on_subtask_start/done`; 14 real wiki pages + 57 miras memories + the chip-decision study provide authentic demo
material.

### A2 · PM — PRD
- **Goal.** A real-time UI + the streaming backend behind it, zero-build and offline, four surfaces → six shipped.
- **FR.** (1) Stream all 7 pillars live; (2) render the council debate persona-by-persona with scores +
  red-team; (3) grow the knowledge graph live; (4) grounded chat; (5) replayable runs; (6) wiki reader;
  (7) backend/model switch + scheduler + metrics; (8) demo mode with no key, static mode with no pip.
- **NFR.** Zero npm/bundler/CDN; offline; additive backend (QA suite unaffected); SSE; distinctive non-generic UI.
- **Out of scope (honest).** Real multi-platform gateways, the self-improving skill loop, a 200+ model registry,
  serverless deploy backends. These are Hermes strengths we do **not** claim to match yet (see Cycle B + `council/`).
- **Success metrics.** 68/68 QA green; 0 console errors; all six surfaces verified in a real browser; a full
  demo run streams 90+ events end-to-end; lint-clean wiki.

### A3 · Architect — Design
- **Event spine.** `agents/events.py::EventBus` — thread-safe fan-out; one typed event schema for live runs,
  recorded replay, and the bundled demo. Pipeline runs in a worker thread; `emit` pushes via
  `loop.call_soon_threadsafe`. Late subscribers get history replayed.
- **Backend.** `api/server.py` adds SSE `/run/{id}/events`, `POST /chat`, `/wiki/graph`, `/memories`,
  `/metrics.json`, `GET|PATCH /config`, serves the UI at `/`. `_can_run_live()` auto-selects demo vs live.
- **Frontend.** `m1frame-studio.html` — hand-rolled CSS (Bahnschrift + Cascadia, offline), vanilla reactive JS,
  a canvas force-graph reused for the mini + full views, one `onEvent` renderer.
- **Three tiers.** FastAPI+key (live) · FastAPI no-key (server replay) · stdlib `studio/serve.py` (client replay).

### A4 · Scrum Master — Stories (all DELIVERED)
1. EventBus + pipeline instrumentation — *additive, default no-op* ✓
2. Demo fixture + static snapshots (`studio/build_demo.py`) ✓
3. FastAPI SSE/chat/graph/config endpoints ✓
4. The six-surface UI (`m1frame-studio.html`) ✓
5. Glue: config / launch / Makefile / requirements / README / CHANGELOG ✓
6. Browser verification (all surfaces, 0 errors) ✓

### A5 · QA Gate 1 — see `QA_GATE.md` (Gate A). Verdict folded in: layout height-chain bug fixed, link dedupe fixed.

---

## CYCLE B — Credibly surpass Hermes (validation & hardening)

### B1 · Analyst — Honest feature-parity matrix (m1frame Studio vs Hermes Agent)

| Capability | Hermes Agent | m1frame Studio | Verdict |
|---|---|---|---|
| **Visible multi-agent deliberation** | ✗ (single self-improving agent) | ✓ live council debate + **independent red-team** that overrides the council | **m1frame far ahead** |
| **Grounded knowledge graph** | partial (curated memory) | ✓ live LLM-wiki constellation + cited chat | **m1frame ahead** |
| **Persistent memory** | ✓ agent-curated + reinforcement | ✓ miras (surprise-gated) — visible feed | **par** |
| **Real-time UI** | ✓ rich TUI | ✓ premium **web** UI, six surfaces, zero-build/offline | **par → m1frame on aesthetics/onboarding** |
| **Run replay / auditability** | partial (session history) | ✓ every run replays from its event trace | **m1frame ahead** |
| **Model flexibility** | ✓ 200+ models, instant switch | ✓ 5 backends, one-line/one-click switch | **Hermes ahead (breadth)** |
| **Multi-platform gateways** (Telegram/Discord/…) | ✓ 6 channels | ✗ | **Hermes ahead** |
| **Self-improving skill loop** | ✓ | ✗ (roadmap) | **Hermes ahead** |
| **Built-in tools / MCP** | ✓ 40+ tools, MCP | partial (OpenPlanter investigation + pipeline) | **Hermes ahead** |
| **Deploy backends** (Docker/SSH/Modal/Daytona…) | ✓ 6 | ✗ (single-file, runs anywhere) | **different goals** |
| **Portability / zero lock-in / offline** | heavy infra | ✓ single file, no CDN, runs offline | **m1frame ahead** |
| **Maturity** | ~10k commits, productized | young, focused | **Hermes ahead** |

**Analyst conclusion (the claim we will let the council attack):** m1frame Studio is **decisively superior on the
axis that matters most for *trust*** — visible, audited, grounded deliberation — and on portability and onboarding.
It is **not** broadly superior across *all* of Hermes' surface area (gateways, skill-learning, tool breadth,
model count, deployment, maturity). "Far superior from anything else" is true **for trustworthy multi-agent
reasoning you can watch**, and is an *overclaim* if stated unconditionally. The honest headline: **"the most
transparent / auditable multi-agent workspace there is"** — and a roadmap to close the remaining Hermes gaps.

> **Red-team footnote (folded in):** row 1's "far ahead" rests on a *real* red-team in `agents/council.py`
> (`review()` runs an adversarial reviewer that can set `verdict=fail` to veto). Its veto changes the gate
> outcome specifically when the council would otherwise have **passed** (score ≥ 7) — i.e. exactly the
> dangerous "overconfident pass" case. When the council already returns *conditional*, the gate is already not
> passed, so the veto is a no-op there by design. We say *"a red-team that can veto a pass"*, not *"that
> overturns every verdict."*

### B2 · PM — What "superior" means + metrics
- **Win condition:** a newcomer, in <60s and with no API key, *sees* a council deliberate, a red-team correct it,
  a graph grow, and gets a cited answer — an experience no competitor offers out of the box.
- **Guardrail:** every comparative claim in README/marketing must be *axis-qualified*; no bare "10000×".

### B3 · Architect — Gap-closing roadmap (post-MVP, explicitly not in this build)
Gateways (start: one webhook→Telegram bridge) · skill-learning loop (persist successful story chains as reusable
skills via miras patterns) · MCP tool surface · model-registry UI. Sequenced so each is additive like the Studio was.

### B4 · Scrum Master — Hardening stories (this cycle)
1. Spawn the Council fact-check (3 specialists ∥ + red-team) on the parity claims + code + UX → `council/`.
2. Fold every blocking finding into code/docs (fix, don't caveat).
3. Re-verify (QA + browser). 4. Ingest verdict to wiki; persist to miras.

### B5 · QA Gate 2 + Council — see `QA_GATE.md` (Gate B) and `council/`.
