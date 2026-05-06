#!/usr/bin/env python3
"""
m1frame — Main Workflow Runner
Correct 6-step pipeline:
  1. BMAD          → story backlog (analyst/architect/dev/qa roles)
  2. Council Brainstorm → personas consult BEFORE generation (gcpdev)
  3. Miras         → execute stories with sequential state handoffs
  4. Karpathy      → <thought> CoT refinement pass
  5. Council Review → QA gate, consensus score ≥ 7 → approved
  6. LLM Wiki      → two-step Analysis→Generation ingest

Usage:
  python scripts/run_workflow.py --goal "Build a FastAPI service with JWT auth"
  python scripts/run_workflow.py --goal "..." --backend ollama
  python -m m1frame --goal "..."
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_client import LLMClient, load_config
from agents.bmad import BMADAgent
from agents.miras import MirasOrchestrator
from agents.karpathy import KarpathyEngine
from agents.council import LLMCouncil
from agents.wiki import LLMWiki


def _bar(text: str) -> None:
    print(f"\n{'═'*62}\n  {text}\n{'═'*62}")

def _step(label: str, detail: str = "") -> None:
    print(f"\n  ▶  {label}")
    if detail:
        print(f"     {detail}")


def run_workflow(
    goal: str,
    backend: str | None = None,
    skip_council: bool = False,
    skip_wiki: bool = False,
    verbose: bool = True,
) -> dict:
    cfg = load_config()
    client = LLMClient(override_backend=backend)
    purpose = Path("purpose.md").read_text() if Path("purpose.md").exists() else ""

    results: dict = {
        "goal": goal, "blueprint": None, "brainstorm": None,
        "state": None, "verdict": None, "wiki_page": None,
    }

    # ── 1. BMAD ──────────────────────────────────────────────────────────────
    _bar("PILLAR 1 · BMAD  —  Story Backlog")
    bmad = BMADAgent(client, config=cfg.get("bmad"))
    blueprint = bmad.plan(goal, extra_context=purpose[:500])
    issues = bmad.validate(blueprint)
    print(f"  {'✓ Blueprint valid' if not issues else '⚠  ' + str(issues)}")
    if verbose:
        print(blueprint.summary())
    results["blueprint"] = blueprint

    # ── 2. Council Brainstorm (pre-generation) ────────────────────────────────
    brainstorm_context = ""
    if not skip_council:
        _bar("PILLAR 2 · COUNCIL BRAINSTORM  —  Pre-Generation")
        council = LLMCouncil(client, config=cfg.get("council"))
        brainstorm = council.brainstorm(task=goal)
        print(brainstorm.summary())
        results["brainstorm"] = brainstorm
        brainstorm_context = (
            f"Council recommended plan: {brainstorm.recommended_plan}\n"
            + "\n".join(f"- {s}" for s in brainstorm.implementation_steps)
            + "\nRisks: " + "; ".join(brainstorm.risks_to_mitigate)
        )
    else:
        council = None

    # ── 3. Miras ─────────────────────────────────────────────────────────────
    _bar("PILLAR 3 · MIRAS  —  Multi-Agent Execution")

    def on_start(story):
        _step(f"[{story.role.upper()}] Story {story.id}: {story.title}")

    def on_done(story, result):
        print(f"     ✓  {result[:100].replace(chr(10),' ')}...")

    miras = MirasOrchestrator(
        client, config=cfg.get("miras"),
        on_subtask_start=on_start, on_subtask_done=on_done,
    )
    ctx = "\n\n".join(filter(None, [purpose[:400], brainstorm_context[:800]]))
    state = miras.run(blueprint, purpose_context=ctx)
    results["state"] = state

    # ── 4. Karpathy ──────────────────────────────────────────────────────────
    _bar("PILLAR 4 · KARPATHY  —  Chain-of-Thought Refinement")
    engine = KarpathyEngine(client, config=cfg.get("karpathy"))
    refined = engine.run(
        prompt=(
            f"Goal: {goal}\n\n"
            f"Synthesise these multi-agent outputs into one complete, coherent response:\n\n"
            f"{state.final_output()[:4000]}"
        ),
        extra_system=purpose[:300],
        refine=True,
    )
    print(f"  ✓  CoT extracted: {'yes' if refined.had_thought_tag else 'no'}")
    if verbose and refined.answer:
        print(f"  Preview: {refined.answer[:180]}...")

    # ── 5. Council Review (QA gate) ───────────────────────────────────────────
    final_output = refined.answer
    if not skip_council:
        _bar("PILLAR 5 · COUNCIL REVIEW  —  QA Gate")
        verdict = council.review(task=goal, output=refined.answer)
        print(verdict.report())
        results["verdict"] = verdict
        final_output = verdict.approved_output

    # ── 6. LLM Wiki ──────────────────────────────────────────────────────────
    if not skip_wiki:
        _bar("PILLAR 6 · LLM WIKI  —  Knowledge Graph Ingest")
        wiki = LLMWiki(client, config=cfg.get("wiki"))
        page = wiki.ingest(raw_text=final_output, topic_hint=goal[:100])
        print(f"  ✓  Saved: wiki/{page.filename}  [{page.page_type}]  tags={page.tags}")
        results["wiki_page"] = page

    _bar("FINAL OUTPUT")
    print(final_output)
    return results


def main() -> None:
    p = argparse.ArgumentParser(description="m1frame — Portable Multi-Agent Workflow")
    p.add_argument("--goal", required=True, help="High-level goal to accomplish")
    p.add_argument("--backend", default=None,
                   help="LLM backend: claude | openai | ollama | vllm | lmstudio")
    p.add_argument("--no-council", action="store_true", help="Skip Council steps")
    p.add_argument("--no-wiki",    action="store_true", help="Skip Wiki ingest")
    p.add_argument("--quiet",      action="store_true", help="Minimal output")
    args = p.parse_args()
    run_workflow(
        goal=args.goal, backend=args.backend,
        skip_council=args.no_council, skip_wiki=args.no_wiki,
        verbose=not args.quiet,
    )

if __name__ == "__main__":
    main()
