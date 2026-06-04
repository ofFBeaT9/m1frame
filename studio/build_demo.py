#!/usr/bin/env python3
"""
studio/build_demo.py — generate studio/demo_run.json

A scripted, *timed* sequence of the SAME events the live pipeline emits
(see agents/events.py), so m1frame Studio shows a gorgeous, fully-working
deliberation with **zero API key and zero pip installs**.

The narrative is a generic, broadly-relatable software decision — "ship the MVP
as a monolith or microservices?" — with a 3-member council + a red-team that
corrects an internal contradiction. It exercises every pillar so a new user sees
exactly how m1frame deliberates, grounds, and remembers.

Run:  python studio/build_demo.py   ->   studio/demo_run.json (+ static snapshots)
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
WIKI = ROOT / "wiki"
STUDIO = Path(__file__).resolve().parent
OUT = STUDIO / "demo_run.json"
STRUCTURAL = {"index", "log", "overview", "purpose"}

GOAL = "Should we ship our MVP as a monolith or microservices?"


# ── pull real wiki nodes so the demo graph matches /wiki/graph ──────────────────

def wiki_nodes() -> list[dict]:
    nodes = []
    for p in sorted(WIKI.rglob("*.md")):
        if p.stem in STRUCTURAL:
            continue
        text = p.read_text(encoding="utf-8")
        mt = re.search(r"^title:\s*(.+)$", text, re.M)
        pt = re.search(r"^page_type:\s*(.+)$", text, re.M)
        if not mt:
            continue
        nodes.append({"id": mt.group(1).strip(),
                      "type": (pt.group(1).strip() if pt else "page")})
    return nodes


def wiki_links(node_ids: set[str]) -> list[dict]:
    link_re = re.compile(r"\[\[([^\]|]+)")
    title_of, links, seen = {}, [], set()
    for p in sorted(WIKI.rglob("*.md")):
        if p.stem in STRUCTURAL:
            continue
        text = p.read_text(encoding="utf-8")
        mt = re.search(r"^title:\s*(.+)$", text, re.M)
        if mt:
            title_of[p] = mt.group(1).strip()
    for p, src in title_of.items():
        for tgt in link_re.findall(p.read_text(encoding="utf-8")):
            tgt = tgt.strip()
            if tgt in node_ids and src in node_ids and src != tgt:
                key = tuple(sorted((src, tgt)))
                if key not in seen:
                    seen.add(key)
                    links.append({"source": src, "target": tgt})
    return links


# ── the scripted run ────────────────────────────────────────────────────────────

def build_events() -> list[dict]:
    """Return [{delay_ms, ...flat_event}] — delay_ms is the pause BEFORE the event."""
    ev: list[dict] = []
    seq = 0

    def e(delay, type, pillar=None, **data):
        nonlocal seq
        seq += 1
        row = {"delay_ms": delay, "type": type, "seq": seq}
        if pillar:
            row["pillar"] = pillar
        row.update(data)
        ev.append(row)

    e(0, "run_start", goal=GOAL, options={
        "backend": "claude (demo replay)", "parallel": False, "self_critique": True})

    # Skill recall (self-improving) — a prior vetted recipe seeds planning
    e(300, "skill_suggested", pillar="bmad", skills=[
        {"id": "b7c2d9e1", "title": "Architecture Decision Recipe", "uses": 2, "score": 8.4}])

    # 1 · BMAD ------------------------------------------------------------------
    e(350, "pillar_start", pillar="bmad", idx=1, label="BMAD · Story Backlog")
    e(700, "bmad_blueprint", pillar="bmad",
      project="MVP Architecture Decision", domain="software architecture",
      mvp="Pick an architecture that ships the MVP fast without blocking future scale",
      issues=[],
      stories=[
          {"id": 1, "title": "Frame the speed-vs-scale tradeoff", "role": "analyst",
           "complexity": "medium", "depends_on": [],
           "acceptance_criteria": ["Decide what 'scale' actually means for this MVP"]},
          {"id": 2, "title": "Investigate the real cost of distributed ops", "role": "investigator",
           "complexity": "high", "depends_on": [1],
           "acceptance_criteria": ["Quantify team-size vs service-count overhead"]},
          {"id": 3, "title": "Design a modular monolith", "role": "architect",
           "complexity": "high", "depends_on": [1],
           "acceptance_criteria": ["Clear module seams; one deploy, many bounded contexts"]},
          {"id": 4, "title": "Plan the service-extraction path", "role": "architect",
           "complexity": "medium", "depends_on": [3],
           "acceptance_criteria": ["A module can become a service without a rewrite"]},
          {"id": 5, "title": "Red-team the microservices hype", "role": "qa",
           "complexity": "high", "depends_on": [2, 3],
           "acceptance_criteria": ["Test the claim that microservices reduce coupling"]},
      ])
    e(500, "pillar_done", pillar="bmad", ms=1180)

    # 2 · Council brainstorm ----------------------------------------------------
    e(300, "pillar_start", pillar="council", idx=2, label="Council · Brainstorm")
    e(450, "council_persona_start", pillar="council", mode="brainstorm", persona="Critic")
    e(900, "council_persona", pillar="council", mode="brainstorm", persona="Critic",
      approach="Attack the premise that microservices are the 'scalable' default.",
      considerations=["A pre-PMF MVP has near-zero scaling pressure"],
      risks=["Premature decomposition spends the team's budget on plumbing, not product"],
      opportunities=["Shipping speed is the only scalability that matters before product-market fit"],
      direction="Optimize for the fastest path to a shippable product, not for hypothetical scale.")
    e(350, "council_persona_start", pillar="council", mode="brainstorm", persona="Advocate")
    e(850, "council_persona", pillar="council", mode="brainstorm", persona="Advocate",
      approach="Steelman a modular monolith with clean seams.",
      considerations=["One deploy, one DB, bounded contexts as modules", "CI stays trivial"],
      risks=["Sloppy modules become a big ball of mud"],
      opportunities=["Refactor in-process now; extract a service later for ~free"],
      direction="Build a modular monolith; keep module boundaries strict so extraction is cheap.")
    e(350, "council_persona_start", pillar="council", mode="brainstorm", persona="Domain Expert")
    e(950, "council_persona", pillar="council", mode="brainstorm", persona="Domain Expert",
      approach="Bound the real cost of distributed systems.",
      considerations=["Network calls add partial-failure, retries, idempotency, tracing",
                      "A 3–6 person team can't staff per-service on-call"],
      risks=["Distributed transactions and eventual consistency dominate early eng time"],
      opportunities=["Conway's Law: ship one service per team you actually have (one)"],
      direction="Don't pay distributed-systems tax before you have the team or the load to justify it.")
    e(800, "council_brainstorm", pillar="council",
      plan="Converge on a modular monolith; treat microservices as a later, trigger-gated extraction.",
      steps=["Quantify the ops tax", "Design strict module seams", "Define extraction triggers", "Red-team the coupling claim"],
      risks=["A 'microservices reduce coupling' claim may hide coupling moving to the network"],
      confidence="high")
    e(400, "pillar_done", pillar="council", ms=4250, phase="brainstorm")

    # 3 · OpenPlanter -----------------------------------------------------------
    e(300, "pillar_start", pillar="openplanter", idx=3, label="OpenPlanter · Investigation")
    e(1100, "openplanter_result", pillar="openplanter", mode="llm+grounded",
      summary=("Investigation across team-size and failure-mode data: below ~15–20 engineers, microservices "
               "overhead (CI/CD per service, network partial-failure handling, distributed tracing, on-call "
               "fan-out) consistently outweighs the scaling benefit for a pre-PMF product. The recurring "
               "failure pattern is 'distributed monolith': services so chatty they must deploy together — "
               "all of the cost of distribution, none of the independence."),
      web_results=3)
    e(450, "pillar_done", pillar="openplanter", ms=1400)

    # 4 · Miras execution -------------------------------------------------------
    e(300, "pillar_start", pillar="miras", idx=4, label="Miras · Multi-Agent Execution")
    for sid, role, title, prev, delay in [
        (1, "analyst", "Frame speed-vs-scale",
         "Before product-market fit, shipping speed dominates; 'scale' is a problem you want to have.", 800),
        (2, "investigator", "Cost of distributed ops",
         "Per-service CI, on-call, and network failure-handling exceed the benefit below ~15–20 engineers.", 850),
        (3, "architect", "Modular monolith design",
         "Bounded contexts as in-process modules behind interfaces; one deploy, one DB, strict seams.", 900),
        (4, "architect", "Service-extraction path",
         "Each module exposes a narrow interface so it can be lifted to a service without a rewrite.", 800),
        (5, "qa", "Red-team the coupling claim",
         "Microservices don't remove coupling — they relocate it to the network, adding partial failure.", 900),
    ]:
        e(250, "story_start", pillar="miras", id=sid, role=role, title=title)
        e(delay, "story_done", pillar="miras", id=sid, role=role, preview=prev)
    e(400, "pillar_done", pillar="miras", ms=5600, stories_done=5)

    # 5 · Karpathy refinement (streamed) ----------------------------------------
    e(300, "pillar_start", pillar="karpathy", idx=5, label="Karpathy · CoT Refinement")
    stream = ("Ship a modular monolith first. Simplicity is the product, not a compromise. Enforce strict "
              "module boundaries now so any module can be extracted into a service the day a real scaling "
              "trigger appears — sustained load a single box can't serve, or a team big enough to own a "
              "service end-to-end. Until then, one deploy beats ten. ").split(" ")
    for word in stream:
        e(60, "karpathy_token", pillar="karpathy", chunk=word + " ")
    e(300, "karpathy_done", pillar="karpathy", had_cot=True,
      thought=("Restate: pick an MVP architecture. Known: pre-PMF has ~no scaling pressure; distributed ops "
               "carry real, constant cost; coupling doesn't vanish under microservices. Therefore the modular "
               "monolith wins now; keep seams strict so extraction is cheap later. Gate splits behind real triggers."),
      answer_preview="Ship a modular monolith; extract services only on a real scaling trigger.")
    e(350, "pillar_done", pillar="karpathy", ms=3900)

    # 6 · Council review (QA gate) + red-team -----------------------------------
    e(300, "pillar_start", pillar="council", idx=6, label="Council · QA Gate Review")
    e(450, "council_persona_start", pillar="council", mode="review", persona="Critic")
    e(800, "council_persona", pillar="council", mode="review", persona="Critic", verdict="conditional",
      score=8, key_points=["Strong, but name the explicit extraction triggers"],
      recommendation="State the split triggers (sustained load / team size / independent deploy need) explicitly.")
    e(300, "council_persona_start", pillar="council", mode="review", persona="Advocate")
    e(750, "council_persona", pillar="council", mode="review", persona="Advocate", verdict="pass",
      score=9, key_points=["Three independent lenses converge on the same answer"],
      recommendation="Ship the decision; the convergence is the signal.")
    e(300, "council_persona_start", pillar="council", mode="review", persona="Domain Expert")
    e(800, "council_persona", pillar="council", mode="review", persona="Domain Expert", verdict="pass",
      score=8, key_points=["Extraction path keeps the door open to services"],
      recommendation="Keep module interfaces narrow so the later split stays a refactor, not a rewrite.")
    e(350, "council_persona_start", pillar="council", mode="review", persona="Red-Team")
    e(950, "council_persona", pillar="council", mode="review", persona="Red-Team", verdict="conditional",
      score=7, key_points=["A council member implied microservices 'eliminate coupling' — FALSE",
                           "They move coupling to the network: partial failure, retries, versioned contracts"],
      recommendation="Drop the 'eliminates coupling' framing; the monolith's in-process coupling is cheaper to change.")
    e(900, "council_verdict", pillar="council", score=8.0, verdict="pass", passed=True,
      summary=("Ship a modular monolith, extraction-ready, with explicit split triggers. The single "
               "'microservices remove coupling' claim was an internal contradiction the red-team removed."),
      required_fixes=["State the extraction triggers explicitly", "Drop the 'eliminates coupling' claim"])
    e(300, "qa_gate", pillar="council", gate="results-review", status="PASS", score=8.0)
    e(350, "pillar_done", pillar="council", ms=6100, phase="review")
    # The pass earned a reinforcement of the vetted skill (self-improving loop)
    e(300, "skill_learned", pillar="council", id="b7c2d9e1",
      title="Architecture Decision Recipe", score=8.4, uses=3)

    # 7 · LLM Wiki ingest — grow the knowledge graph ----------------------------
    nodes = wiki_nodes()
    ids = {n["id"] for n in nodes}
    links = wiki_links(ids)
    e(300, "pillar_start", pillar="wiki", idx=7, label="LLM Wiki · Knowledge Graph Ingest")
    chunk: list[dict] = []
    for i, n in enumerate(nodes):
        chunk.append(n)
        if len(chunk) == 2 or i == len(nodes) - 1:
            e(160, "graph_delta", pillar="wiki", nodes=list(chunk), links=[])
            chunk = []
    e(220, "graph_delta", pillar="wiki", nodes=[], links=links)
    e(300, "wiki_page", pillar="wiki", title="MVP Architecture Decision",
      page_type="synthesis", filename="synthesis/mvp-architecture-decision.md",
      tags=["architecture", "monolith", "microservices", "decision"])
    e(350, "pillar_done", pillar="wiki", ms=2100)

    # miras memory feed ---------------------------------------------------------
    for delay, mtype, agent, text in [
        (300, "decision", "architect",
         "SHIP A MODULAR MONOLITH first; keep strict module seams so a service can be extracted later for ~free."),
        (260, "constraint", "qa",
         "RED-TEAM LESSON: microservices don't remove coupling — they relocate it to the network (partial failure, retries)."),
        (260, "decision", "analyst",
         "KEY PRINCIPLE: before product-market fit, shipping speed dominates hypothetical scale."),
    ]:
        e(delay, "memory_added", type_=mtype, agent=agent, text=text)

    # final ---------------------------------------------------------------------
    e(500, "final",
      output=("# Decision: ship a modular monolith (extraction-ready)\n\n"
              "**Not microservices — not yet.**\n\n"
              "1. **Build one deployable, many bounded contexts.** Model each domain as an in-process module "
              "behind a narrow interface, with one database and trivial CI. Simplicity is a feature.\n"
              "2. **Keep the seams strict.** Because modules talk through interfaces, any one can be lifted into "
              "a standalone service later **without a rewrite**.\n"
              "3. **Don't split yet — gate it on real triggers:** sustained load a single box can't serve, a "
              "team large enough to own a service end-to-end, or a genuine need for independent deploys.\n"
              "4. **Why the monolith wins now:** before product-market fit there is ~no scaling pressure, and "
              "distributed systems carry constant ops cost — microservices **relocate** coupling to the network "
              "rather than removing it.\n\n"
              "*Three independent lenses — product, operations, architecture — converged on the same answer. "
              "The lone 'microservices remove coupling' dissent was self-disqualified by the red-team.*"),
      score=8.0, passed=True, wiki_page="synthesis/mvp-architecture-decision.md")
    e(200, "done", ms=38240)
    return ev


def _memories_from_events(events: list[dict]) -> list[dict]:
    """Build the static memory snapshot from the demo's own memory_added events
    (so the clean release carries no external/project memory file)."""
    out = []
    for r in events:
        if r.get("type") == "memory_added":
            out.append({"type": r.get("type_", "memory"), "agent": r.get("agent", ""),
                        "text": r.get("text", ""), "tags": ""})
    return out


def main() -> int:
    events = build_events()
    payload = {
        "version": 1,
        "goal": GOAL,
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "duration_ms": sum(r["delay_ms"] for r in events),
        "events": events,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    types = sorted({r["type"] for r in events})
    print(f"[OK] {OUT.relative_to(ROOT)}  —  {len(events)} events, "
          f"{payload['duration_ms']/1000:.1f}s timeline")
    print("     event types:", ", ".join(types))

    # Static snapshots so the UI is fully alive even with NO server / NO pip.
    from dataclasses import asdict

    from agents.skills import SkillLibrary
    from studio import data
    snapshots = {
        "wiki_graph.json": data.wiki_graph(),
        "wiki_pages.json": data.wiki_pages(),
        "memories.json": _memories_from_events(events),
        "skills.json": [asdict(s) for s in SkillLibrary().all()],
    }
    for name, obj in snapshots.items():
        (STUDIO / name).write_text(json.dumps(obj, indent=2), encoding="utf-8")
    g = snapshots["wiki_graph.json"]
    print(f"[OK] static snapshots: wiki_graph ({len(g['nodes'])} nodes, "
          f"{len(g['links'])} links), {len(snapshots['wiki_pages.json'])} pages, "
          f"{len(snapshots['memories.json'])} memories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
