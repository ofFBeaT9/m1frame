#!/usr/bin/env python3
"""
studio/build_demo.py — generate studio/demo_run.json

A scripted, *timed* sequence of the SAME events the live pipeline emits
(see agents/events.py), so m1frame Studio shows a gorgeous, fully-working
deliberation with **zero API key and zero pip installs**.

The narrative is the project's real BMAD cycle-2 decision — "what chip should we
manufacture?" — a 3-member council + a red-team that corrected an internal
contradiction. Content is drawn from the actual artifacts in this repo
(chip_decision/, opu_study/results/summary.json, wiki/) so the demo is honest,
not invented marketing.

Run:  python studio/build_demo.py   ->   studio/demo_run.json
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

GOAL = ("What chip should we manufacture for the Tritone medical accelerator — "
        "an analog optical processor, or a digital ternary ASIC?")


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

    # 1 · BMAD ------------------------------------------------------------------
    e(350, "pillar_start", pillar="bmad", idx=1, label="BMAD · Story Backlog")
    e(700, "bmad_blueprint", pillar="bmad",
      project="Tritone Chip Decision", domain="medical edge AI / silicon",
      mvp="Pick a manufacturable compute substrate that clears the FDA bar",
      issues=[],
      stories=[
          {"id": 1, "title": "Frame the determinism-vs-efficiency tradeoff", "role": "analyst",
           "complexity": "medium", "depends_on": [],
           "acceptance_criteria": ["Bit-exactness defined as FDA prerequisite"]},
          {"id": 2, "title": "Investigate photonic MVM noise floor", "role": "investigator",
           "complexity": "high", "depends_on": [1],
           "acceptance_criteria": ["Static-defect floor quantified from OPU study"]},
          {"id": 3, "title": "Design digital ternary datapath", "role": "architect",
           "complexity": "high", "depends_on": [1],
           "acceptance_criteria": ["Multiplier-free {-1,0,+1}; 42% zeros skipped"]},
          {"id": 4, "title": "Cross-check regulatory path (510k)", "role": "architect",
           "complexity": "medium", "depends_on": [1],
           "acceptance_criteria": ["Determinism maps to SaMD locked-algorithm rule"]},
          {"id": 5, "title": "Red-team the analog 'win'", "role": "qa",
           "complexity": "high", "depends_on": [2, 3],
           "acceptance_criteria": ["Classify each CIM macro analog vs digital"]},
      ])
    e(500, "pillar_done", pillar="bmad", ms=1180)

    # 2 · Council brainstorm ----------------------------------------------------
    e(300, "pillar_start", pillar="council", idx=2, label="Council · Brainstorm")
    e(450, "council_persona_start", pillar="council", mode="brainstorm", persona="Critic")
    e(900, "council_persona", pillar="council", mode="brainstorm", persona="Critic",
      approach="Attack the premise that efficiency is the objective.",
      considerations=["TOPS/W is the wrong metric for N≈4 regulated inference"],
      risks=["Chasing analog efficiency forfeits bit-exactness"],
      opportunities=["Determinism is a structural moat, not a tuning knob"],
      direction="Optimize for the cheapest bit-exact design that clears FDA, not peak TOPS/W.")
    e(350, "council_persona_start", pillar="council", mode="brainstorm", persona="Advocate")
    e(850, "council_persona", pillar="council", mode="brainstorm", persona="Advocate",
      approach="Steelman a small digital ternary ASIC.",
      considerations=["SKY130 open MPW ~ $10-12k NRE", "Cortex-M33 host for weight load"],
      risks=["Tape-out before clinical volume wastes NRE"],
      opportunities=["Frozen-model edge inference at sub-10 mW"],
      direction="Build digital ternary; gate the tape-out behind real triggers.")
    e(350, "council_persona_start", pillar="council", mode="brainstorm", persona="Domain Expert")
    e(950, "council_persona", pillar="council", mode="brainstorm", persona="Domain Expert",
      approach="Bound the photonics physics from the OPU study.",
      considerations=["7.8% static-defect value floor more SNR cannot remove",
                      "~262 W tuning for a 512x512 MZI mesh; E/O-O/E overhead below N≈4096"],
      risks=["Derivatives ~6x more fragile than values under analog noise"],
      opportunities=["Optics OK only as inference-only accelerator for a frozen PINN"],
      direction="Reject optical training/gradients; analog cannot meet the accuracy budget.")
    e(800, "council_brainstorm", pillar="council",
      plan="Converge on a deterministic digital ternary chip; treat optics as inference-only at best.",
      steps=["Quantify analog floor", "Design digital datapath", "Map to 510(k)", "Red-team analog CIM"],
      risks=["An analog CIM 'win' may hide an ADC that breaks determinism"],
      confidence="high")
    e(400, "pillar_done", pillar="council", ms=4250, phase="brainstorm")

    # 3 · OpenPlanter -----------------------------------------------------------
    e(300, "pillar_start", pillar="openplanter", idx=3, label="OpenPlanter · Investigation")
    e(1100, "openplanter_result", pillar="openplanter", mode="llm+grounded",
      summary=("OPU feasibility sim (ternary PINN, bit-exact baseline + optical-noise model, "
               "sparsity 42.4%): VALUES survive analog optics but DERIVATIVES do not. Value "
               "error crosses the 19.4% ternary budget at optical SNR ~18.2 dB/layer with a "
               "static-defect floor ~7.8%. A 2% photonic weight defect with zero readout noise "
               "already gives 8.1% value error but 51.9% derivative error (~6x fragility gap)."),
      web_results=3)
    e(450, "pillar_done", pillar="openplanter", ms=1400)

    # 4 · Miras execution -------------------------------------------------------
    e(300, "pillar_start", pillar="miras", idx=4, label="Miras · Multi-Agent Execution")
    for sid, role, title, prev, delay in [
        (1, "analyst", "Frame determinism-vs-efficiency",
         "For a regulated, edge, small-N medical workload, determinism dominates efficiency.", 800),
        (2, "investigator", "Photonic MVM noise floor",
         "Static-defect floor ~7.8% value error; derivatives never reach the budget at any SNR.", 850),
        (3, "architect", "Digital ternary datapath",
         "Weights ∈ {-1,0,+1} → mux + conditional add; 42% zeros skipped; bit-exact integer path.", 900),
        (4, "architect", "Regulatory path",
         "Bit-exact inference maps to the SaMD locked-algorithm rule; analog non-determinism fails 510(k).", 800),
        (5, "qa", "Red-team the analog win",
         "Charge-domain SRAM CIM is NOT bit-exact (ADC + PVT). Only fully-digital ternary CIM qualifies.", 900),
    ]:
        e(250, "story_start", pillar="miras", id=sid, role=role, title=title)
        e(delay, "story_done", pillar="miras", id=sid, role=role, preview=prev)
    e(400, "pillar_done", pillar="miras", ms=5600, stories_done=5)

    # 5 · Karpathy refinement (streamed) ----------------------------------------
    e(300, "pillar_start", pillar="karpathy", idx=5, label="Karpathy · CoT Refinement")
    stream = ("Manufacture a fully-digital, multiplier-free ternary ASIC. Determinism is the "
              "product, not a side effect. Two phases, trigger-gated: SKY130 open-MPW prototype "
              "as a golden-vector vehicle, then TSMC 22/28 nm production with a Cortex-M33 host "
              "and SHA-256-verified weight load. ").split(" ")
    for i, word in enumerate(stream):
        e(60, "karpathy_token", pillar="karpathy", chunk=word + " ")
    e(300, "karpathy_done", pillar="karpathy", had_cot=True,
      thought=("Restate: pick a compute substrate. Known: optics fails the derivative budget and "
               "has a 7.8% floor; digital ternary is bit-exact. FDA needs determinism. Therefore "
               "digital wins; optics is at most inference-only. Gate the tape-out behind triggers."),
      answer_preview="Manufacture a fully-digital ternary ASIC, trigger-gated, SKY130 → 28 nm.")
    e(350, "pillar_done", pillar="karpathy", ms=3900)

    # 6 · Council review (QA gate) + red-team -----------------------------------
    e(300, "pillar_start", pillar="council", idx=6, label="Council · QA Gate Review")
    e(450, "council_persona_start", pillar="council", mode="review", persona="Critic")
    e(800, "council_persona", pillar="council", mode="review", persona="Critic", verdict="conditional",
      score=8, key_points=["Strong, but name the explicit tape-out triggers"],
      recommendation="Add the >500-unit / sub-5mW / 510(k) trigger gate explicitly.")
    e(300, "council_persona_start", pillar="council", mode="review", persona="Advocate")
    e(750, "council_persona", pillar="council", mode="review", persona="Advocate", verdict="pass",
      score=9, key_points=["Three independent lenses converge on the same answer"],
      recommendation="Ship the decision; the convergence is the signal.")
    e(300, "council_persona_start", pillar="council", mode="review", persona="Domain Expert")
    e(800, "council_persona", pillar="council", mode="review", persona="Domain Expert", verdict="pass",
      score=8, key_points=["Photonics correctly bounded to inference-only"],
      recommendation="Keep optics on the roadmap only for frozen linear layers.")
    e(350, "council_persona_start", pillar="council", mode="review", persona="Red-Team")
    e(950, "council_persona", pillar="council", mode="review", persona="Red-Team", verdict="conditional",
      score=7, key_points=["A council member called charge-domain CIM 'fully deterministic' — FALSE",
                           "It accumulates analog charge and reads via ADC (PVT, offset, coupling)"],
      recommendation="Drop charge-domain CIM from the deterministic set; only digital ternary CIM is bit-exact.")
    e(900, "council_verdict", pillar="council", score=8.0, verdict="pass", passed=True,
      summary=("Build a fully-digital ternary ASIC, trigger-gated (SKY130 → 28 nm). The single analog "
               "'win' was an internal contradiction the red-team removed."),
      required_fixes=["State tape-out triggers explicitly", "Remove charge-domain CIM from the bit-exact set"])
    e(300, "qa_gate", pillar="council", gate="results-review", status="PASS", score=8.0)
    e(350, "pillar_done", pillar="council", ms=6100, phase="review")

    # 7 · LLM Wiki ingest — grow the knowledge graph ----------------------------
    nodes = wiki_nodes()
    ids = {n["id"] for n in nodes}
    links = wiki_links(ids)
    e(300, "pillar_start", pillar="wiki", idx=7, label="LLM Wiki · Knowledge Graph Ingest")
    # reveal real nodes progressively, then their links
    chunk: list[dict] = []
    for i, n in enumerate(nodes):
        chunk.append(n)
        if len(chunk) == 2 or i == len(nodes) - 1:
            e(160, "graph_delta", pillar="wiki", nodes=list(chunk), links=[])
            chunk = []
    e(220, "graph_delta", pillar="wiki", nodes=[], links=links)
    e(300, "wiki_page", pillar="wiki", title="Chip Manufacturing Decision",
      page_type="synthesis", filename="synthesis/chip-manufacturing-decision.md",
      tags=["tritone", "chip", "decision"])
    e(350, "pillar_done", pillar="wiki", ms=2100)

    # miras memory feed ---------------------------------------------------------
    for delay, mtype, agent, text in [
        (300, "decision", "architect",
         "MANUFACTURE A FULLY-DIGITAL multiplier-free TERNARY ASIC (bit-exact). Two phases, trigger-gated."),
        (260, "constraint", "qa",
         "RED-TEAM LESSON: charge-domain SRAM CIM is NOT bit-exact (ADC + PVT). Only fully-digital ternary CIM is."),
        (260, "decision", "analyst",
         "KEY PRINCIPLE: for a regulated, edge, small-N medical workload, determinism dominates efficiency."),
    ]:
        e(delay, "memory_added", type_=mtype, agent=agent, text=text)

    # final ---------------------------------------------------------------------
    e(500, "final",
      output=("# Decision: build a fully-digital ternary ASIC\n\n"
              "**Not analog. Not photonic. Not charge-domain CIM.**\n\n"
              "1. **Two phases, trigger-gated:** SKY130 open-MPW prototype (golden-vector vehicle) → "
              "TSMC 22/28 nm production (digital ternary CIM or scaled systolic) + Cortex-M33 host, "
              "SHA-256-verified weight load.\n"
              "2. **Don't tape out yet.** Triggers: >~500 clinical units, a sub-5 mW envelope the FPGA "
              "can't meet, or a 510(k) needing certified silicon. Until then the $20 FPGA + MCU is right.\n"
              "3. **The ultimate system is a lifecycle:** cloud-train (exact gradients) → freeze + certify "
              "(golden vectors, SHA-256 weight lock, SBOM) → edge bit-exact digital-ternary inference.\n"
              "4. **Why digital wins:** for a regulated medical workload, **determinism dominates "
              "efficiency** — bit-exactness is an FDA prerequisite, and analog forfeits it.\n\n"
              "*Three independent lenses — silicon, physics, regulation — converged on the same answer. "
              "The lone analog dissent was self-disqualified by its own determinism rule.*"),
      score=8.0, passed=True, wiki_page="synthesis/chip-manufacturing-decision.md")
    e(200, "done", ms=38240)
    return ev


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

    # Static snapshots so the UI is fully alive even with NO server / NO pip
    # (the stdlib static server or a double-click fetches these directly).
    from studio import data
    snapshots = {
        "wiki_graph.json": data.wiki_graph(),
        "wiki_pages.json": data.wiki_pages(),
        "memories.json": data.load_memories(),
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
