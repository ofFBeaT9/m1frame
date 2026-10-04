---
description: Run the full m1frame pipeline (miras + BMAD + agent council + LLM-wiki knowledge graph) on a question/topic
argument-hint: <question or topic to investigate>
---

# /m1frame — orchestrate the whole stack

You are running the **m1frame** pipeline end-to-end on this topic:

> **$ARGUMENTS**

Execute the phases below in order. This is the exact pipeline proven on the OPU study and the chip decision.
Be rigorous, keep things grounded, and **save all results to a dedicated folder** named after the topic
(e.g. `studies/<slug>/`). Mark a chapter at the start.

## 0. Recall (miras)
- `miras_get_context` and `miras_recall` on the topic BEFORE deciding anything. Surface prior decisions,
  constraints, and any contradictions. Never re-derive what memory already holds.

## 1–4. BMAD planning (embody the personas, label each)
1. **Analyst** → a Project Brief (problem, grounded anchors, the core hypothesis).
2. **PM** → a PRD (goal, FR/NFR, success metrics, explicit out-of-scope).
3. **Architect** → the technical design (be concrete and falsifiable).
4. **Scrum Master** → an Epic + sharded stories with acceptance criteria.
Write these to `studies/<slug>/ROADMAP.md`. Store each handoff to miras with the right `source_agent`.

## 5. QA gate 1 — review the roadmap (before any build)
- Critically review the roadmap for correctness/feasibility. Record findings + a gate
  (PASS/CONCERNS/FAIL) in `studies/<slug>/QA_GATE.md`. **Fold every fix into the build** — don't just caveat.

## 6. Dev — execute
- Implement and RUN it (code + tests + artifacts). Prove it: tests pass, numbers produced, figures rendered.
  Bit-exact/deterministic baselines where applicable. Save artifacts under `studies/<slug>/`.

## 7. Council — multi-agent perspectives (spawn real agents)
- Spawn 2–4 specialist sub-agents IN PARALLEL (e.g. via the Agent tool, `model: sonnet`), each a distinct
  lens on the question. Give each the grounded context so they don't start cold. Collect their position papers.
- Then spawn ONE **red-team / QA** agent to attack the synthesis and find overclaims/contradictions.
- Save all papers to `studies/<slug>/council/`. Resolve contradictions explicitly (don't average them).

## 8. QA gate 2 — results review
- Independent audit of the executed work + the council synthesis. Append the gate to `QA_GATE.md`.

## 9. Knowledge graph (LLM wiki, per CLAUDE.md)
- Two-step ingest: **Analysis** (entities/concepts/connections/contradictions) → **Generation** (write pages).
- Add/update pages under `wiki/` (entities, concepts, synthesis, sources, the saved query) with YAML
  frontmatter + `[[WikiLinks]]`; update `wiki/index.md` and append to `wiki/log.md`.
- Run `python wiki/lint.py` and ensure **0 errors / 0 orphans**.

## 10. Persist + report + visualize
- Store the final decision + any reusable lessons to miras (high `force` only if critical).
- Write `studies/<slug>/FINAL_REPORT.md`: the verdict, the evidence, the caveats, next steps.
- Refresh the dashboard: `python m1frame/build_dashboard.py` and report that it's lint-clean and renders.
- End with a crisp, decisive answer to the original question.

**Principles:** ground every claim; fix don't caveat; one independent red-team beats ten agreeable agents;
prefer the cheap experiment before the expensive commitment; report outcomes faithfully (failures included).
