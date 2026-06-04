# Red-Team Pass — attack on the post-fix synthesis (BMAD Cycle B)

An independent red-team agent attacked the deliverable *after* the council fixes landed. **VERDICT: conditional ·
SCORE 6/10** — it found **two real residual issues the 3-member council missed or misstated**, plus a heading-level
overclaim. All folded in (fix, don't caveat). This is the methodology working: one sharp red-team > ten agreeable
reviewers.

## Findings + disposition

| # | Finding | Severity | Disposition |
|---|---|---|---|
| 1 | **Graph physics rAF ignored `prefers-reduced-motion`** — the synthesis claimed "graph physics paused"; the code did not. The force-directed graph (most motion-intense element) ran at 60fps regardless. | BLOCKER | **FIXED** — `m1frame-studio.html` `Graph` now reads `prefers-reduced-motion` and **freezes node positions after a ~260-frame settle** (layout still resolves; no perpetual motion; hover highlight still redraws). |
| 2 | **`_safe_webhook` allowed loopback + RFC-1918 + `::1`** — only blocked link-local/metadata, leaving SSRF to `127.0.0.1:8080/config` and internal services open. | BLOCKER | **FIXED** — `api/server.py::_safe_webhook` now rejects `is_private/is_loopback/is_link_local/is_reserved/is_multicast/is_unspecified` IP literals + `localhost`. DNS-rebinding limitation documented. |
| 3 | **`_MODEL_RE` allowed `:`** — a YAML foot-gun (the comment said "reject YAML injection"). Not actually exploitable (colon-without-space is a scalar), but a future hazard. | MINOR | **FIXED** — dropped `:` from the charset; model names never use it. |
| 4 | **Red-team veto only changes the gate when the council returned `pass`** — when the council says `conditional`, `passed` is already `False`, so the veto is a no-op there. The "overrides the council" rhetoric overstates scope. | MAJOR (rhetoric) | **FIXED (docs)** — ROADMAP B1 footnote clarifies the veto fires on the *overconfident-pass* case; we now say "a red-team that can **veto a pass**," not "overturns every verdict." The behaviour is correct (you needn't veto a non-pass). |
| 5 | **README heading "Why this beats a single-shot agent"** — Hermes is a self-improving *multi-agent* system, not single-shot; heading invites a general-superiority misread. | MAJOR (rhetoric) | **FIXED** — reworded to "Why m1frame is the most *auditable* multi-agent workspace," with an explicit "we do not out-feature every agent; Hermes leads on X/Y/Z" disclaimer linking the parity matrix. |
| 6 | **`[[wiki]]` `data-wiki` escaping incomplete** | — | **Red-team concluded NOT exploitable** in a conformant browser (double-quoted attr, `&`/`<`/`>` pre-encoded, `"`→`&quot;`); `safeHref` blocks `javascript:`. No change. |
| 7 | **`_new_run` eviction "not thread-safe"** | MAJOR (claimed) | **Triaged — not a real race.** FastAPI handlers run on a single asyncio loop and `_new_run` has **no `await`**, so it executes atomically; no interleaving is possible. Cross-thread mutation only touches per-run keys (in `run_in_executor`), never the `_RUNS` structure. Documented; no lock needed. |

## Net

Two genuine security/accessibility blockers closed; competitive claims tightened to be axis-honest. The red-team's
own assessment: *"This build is close — two targeted fixes (graph motion guard, SSRF blocklist completion) would
bring it to a clean pass."* Both are now done → re-verify in `QA_GATE.md` (Gate B).
