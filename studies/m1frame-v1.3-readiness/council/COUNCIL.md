# Council — m1frame v1.3 Readiness (inline, lightweight)

Three lenses + one independent red-team. Grounded in commit `3c3b6f9`, 90/90 QA.

---

## Lens 1 — Parity (vs Hermes) · score 8/10 · PASS-WITH-NOTES
v1.3 genuinely closes *architecture* gaps that were real in v1.2: gateways exist (5 platforms, one router),
a tool surface exists (registry + MCP client), runs persist + search, providers + Docker landed. That moves
m1frame from "great dashboard, thin agent" to "credible agent with a best-in-class observability story."
**But:** Hermes still wins **breadth** — 40+ tools vs our 5; 8 gateway platforms vs our 5 (3 of ours
live-untested without creds); 6 deploy targets vs our 1 (Docker). **Verdict:** parity on *shape*, not on *surface
area*. Do not claim "superior overall."

## Lens 2 — Reliability / Operability · score 9/10 · PASS
The isolation invariant is the strongest part of this release: every new entry point is best-effort, and
`t_gw_handler_never_crashes` plus the wrapped persistence/skills code mean the blast radius of a new subsystem is
a message, not a dead run. Atomic persistence + partial-tolerant reload are correct. SSRF is centralized in
`agents/net.py`. 90/90 offline, no key needed → reproducible. This is production-grade *engineering hygiene*.

## Lens 3 — UX / Adoption · score 8/10 · PASS
A new user can: `docker compose up` → see the Studio in demo mode with no key; watch a full deliberation incl.
skill recall/learned; ping the gateway and run a tool from Settings; read a real MANUAL. The "always works in
three tiers" property is rare and demo-able. Friction remaining: the 5 built-in tools are minimal, and gateway
setup still needs per-platform tokens (documented, not guided). Good enough to ship; obvious next polish.

## Synthesis (resolve, don't average)
Consensus **8.3/10**. The three lenses agree on the *verdict* and disagree only on emphasis: Parity says "don't
overclaim breadth," Reliability says "the engineering is ready," UX says "the on-ramp is excellent." All three are
simultaneously true → **GO for the positioning** ("most auditable workspace"), **NOT** "beats Hermes overall."

---

## Red-Team — attack the synthesis (can veto)
- **R1 [MAJOR → folded]** `/run` was matched by `startswith("/run")`, so `/runner …` would be mis-routed as a run.
  *Real.* Fixed in `gateways/router.py` + `api/server.py` to require `"/run"` or `"/run "`.
- **R2 [MAJOR → folded]** miras still says "gateways/MCP-tools/deploy = roadmap," now false after v1.3.
  *Real.* Stale memory → updated at report time (don't let memory overclaim *against* us either).
- **R3 [claimed BLOCKER → FALSE]** "MCP client is vaporware." *Rejected:* it's labelled scaffolding in code +
  MANUAL, not counted as a working tool; the *registry* is the tested deliverable. No overclaim made.
- **R4 [MINOR → by design]** Gateway outbound `deliver()` silently returns False without creds. *Intended* —
  the endpoint still returns the reply text; delivery is opportunistic. Documented.

**Red-team verdict:** no unfixed BLOCKER. The 2 real findings are folded. **Does not veto** the PASS.
