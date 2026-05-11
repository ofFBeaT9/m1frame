#!/usr/bin/env python3
"""
m1frame — Main Workflow Runner
7-pillar pipeline:
  1. BMAD              → story backlog (analyst/architect/dev/qa/investigator roles)
  2. Council Brainstorm→ personas consult BEFORE generation
  3. OpenPlanter       → investigation pass (auto-invoked for investigator stories)
  4. Miras             → execute all stories with sequential state handoffs
  5. Karpathy          → <thought> CoT refinement + optional self-critique
  6. Council Review    → QA gate, consensus ≥ 7 → approved
  7. LLM Wiki          → two-step Analysis→Generation ingest

New in v1.1:
  --stream        stream Karpathy tokens to stdout in real time
  --parallel      run independent Miras stories concurrently
  --self-critique use Karpathy self-critique loop instead of single-pass
  --webhook URL   POST result JSON to URL on completion
  --metrics PORT  expose Prometheus /metrics on this port (default: off)

Usage:
  python scripts/run_workflow.py --goal "Investigate vendor payments against lobbying"
  python scripts/run_workflow.py --goal "..." --backend ollama --parallel --stream
  python scripts/run_workflow.py --goal "..." --no-council --no-wiki
  python -m m1frame --goal "..."
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_client import LLMClient, load_config
from agents.bmad import BMADAgent, BMAD_ROLES
from agents.miras import MirasOrchestrator
from agents.karpathy import KarpathyEngine
from agents.council import LLMCouncil
from agents.wiki import LLMWiki
from agents.openplanter import OpenPlanterAgent
from agents.logger import PillarLogger
from agents.metrics import get_metrics


def _bar(text: str) -> None:
    print(f"\n{'═'*62}\n  {text}\n{'═'*62}")

def _step(label: str, detail: str = "") -> None:
    print(f"\n  ▶  {label}")
    if detail:
        print(f"     {detail}")


def _fire_webhook(url: str, payload: dict) -> None:
    """POST result payload to webhook URL — non-fatal."""
    try:
        import urllib.request, json
        data = json.dumps(payload, default=str).encode()
        req = urllib.request.Request(url, data=data,
              headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:
        print(f"  ⚠  Webhook delivery failed: {exc}")


def run_workflow(
    goal: str,
    backend: str | None = None,
    skip_council: bool = False,
    skip_wiki: bool = False,
    skip_openplanter: bool = False,
    verbose: bool = True,
    stream: bool = False,
    parallel: bool = False,
    self_critique: bool = False,
    webhook_url: str | None = None,
    metrics_port: int | None = None,
) -> dict:
    cfg = load_config()
    client = LLMClient(override_backend=backend)
    purpose = Path("purpose.md").read_text() if Path("purpose.md").exists() else ""
    logger = PillarLogger()
    metrics = get_metrics()

    if metrics_port:
        metrics.expose_http(port=metrics_port)
        print(f"  📊  Prometheus metrics at http://localhost:{metrics_port}/metrics")

    results: dict = {
        "goal": goal, "blueprint": None, "brainstorm": None,
        "investigation": None, "state": None, "verdict": None, "wiki_page": None,
    }

    # ── 1. BMAD — Story Backlog ───────────────────────────────────────────────
    _bar("PILLAR 1 · BMAD  —  Story Backlog")
    t0 = time.perf_counter()
    bmad = BMADAgent(client, config=cfg.get("bmad"))
    blueprint = bmad.plan(goal, extra_context=purpose[:500])
    issues = bmad.validate(blueprint)
    print(f"  {'✓ Blueprint valid' if not issues else '⚠  ' + str(issues)}")
    if verbose:
        print(blueprint.summary())
    results["blueprint"] = blueprint
    ms = (time.perf_counter() - t0) * 1000
    metrics.record("bmad", ms=ms)
    logger.timing("bmad", ms=ms, stories=len(blueprint.stories))

    # ── 2. Council Brainstorm ─────────────────────────────────────────────────
    brainstorm_context = ""
    council = None
    if not skip_council:
        _bar("PILLAR 2 · COUNCIL BRAINSTORM  —  Pre-Generation")
        t0 = time.perf_counter()
        council = LLMCouncil(client, config=cfg.get("council"))
        brainstorm = council.brainstorm(task=goal)
        print(brainstorm.summary())
        results["brainstorm"] = brainstorm
        brainstorm_context = (
            f"Council plan: {brainstorm.recommended_plan}\n"
            + "\n".join(f"- {s}" for s in brainstorm.implementation_steps)
            + "\nRisks: " + "; ".join(brainstorm.risks_to_mitigate)
        )
        ms = (time.perf_counter() - t0) * 1000
        metrics.record("council_brainstorm", ms=ms)
        logger.timing("council", ms=ms, mode="brainstorm", confidence=brainstorm.confidence)

    # ── 3. OpenPlanter — Investigation Pass ───────────────────────────────────
    investigation_context = ""
    has_investigator_stories = any(
        getattr(s, "role", "") == "investigator" for s in blueprint.stories
    )
    if not skip_openplanter and has_investigator_stories:
        _bar("PILLAR 3 · OPENPLANTER  —  Investigation")
        t0 = time.perf_counter()
        op_cfg = cfg.get("openplanter", {})
        planter = OpenPlanterAgent(
            client,
            config=op_cfg,
            workspace=op_cfg.get("workspace", "workspace"),
        )
        print(f"  Mode: {planter.mode}")
        inv_result = planter.investigate(task=goal)
        print(inv_result.report())
        results["investigation"] = inv_result
        investigation_context = f"\nInvestigation findings:\n{inv_result.summary}"
        ms = (time.perf_counter() - t0) * 1000
        metrics.record("openplanter", ms=ms)
        logger.timing("openplanter", ms=ms, web_results=len(inv_result.web_results))
    elif not skip_openplanter:
        _bar("PILLAR 3 · OPENPLANTER  —  Skipped (no investigator stories)")

    # ── 4. Miras — Execute Stories ────────────────────────────────────────────
    _bar("PILLAR 4 · MIRAS  —  Multi-Agent Execution" + (" (parallel)" if parallel else ""))

    def on_start(story):
        _step(f"[{story.role.upper()}] Story {story.id}: {story.title}")

    def on_done(story, result):
        print(f"     ✓  {result[:100].replace(chr(10),' ')}...")

    t0 = time.perf_counter()
    miras = MirasOrchestrator(
        client, config=cfg.get("miras"),
        on_subtask_start=on_start, on_subtask_done=on_done,
    )
    ctx = "\n\n".join(filter(None, [purpose[:400], brainstorm_context[:600], investigation_context[:400]]))
    state = miras.run_parallel(blueprint, purpose_context=ctx) if parallel else miras.run(blueprint, purpose_context=ctx)
    results["state"] = state
    ms = (time.perf_counter() - t0) * 1000
    metrics.record("miras", ms=ms)
    logger.timing("miras", ms=ms, parallel=parallel, stories_done=len(state.outputs))

    # ── 5. Karpathy — Refinement ──────────────────────────────────────────────
    _bar("PILLAR 5 · KARPATHY  —  Chain-of-Thought Refinement" + (" + Self-Critique" if self_critique else ""))
    t0 = time.perf_counter()
    engine = KarpathyEngine(client, config=cfg.get("karpathy"))
    synthesis_prompt = (
        f"Goal: {goal}\n\n"
        f"Synthesise these multi-agent outputs into one complete, coherent response:\n\n"
        f"{state.final_output()[:4000]}"
    )

    if stream:
        # Streaming mode: print tokens in real time, then parse the full response
        print("  ▶  Streaming Karpathy refinement...")
        chunks = []
        for chunk in client.stream(
            prompt=synthesis_prompt,
            system=engine.cfg.get("extra_system", purpose[:300]),
            temperature=engine.temperature,
        ):
            print(chunk, end="", flush=True)
            chunks.append(chunk)
        print()
        full_raw = "".join(chunks)
        refined = engine._parse(full_raw)
    elif self_critique:
        refined = engine.self_critique(synthesis_prompt, extra_system=purpose[:300])
        print("  ✓  Self-critique complete")
    else:
        refined = engine.run(
            prompt=synthesis_prompt,
            extra_system=purpose[:300],
            refine=True,
        )

    print(f"  ✓  CoT extracted: {'yes' if refined.had_thought_tag else 'no'}")
    if verbose and refined.answer:
        print(f"  Preview: {refined.answer[:180]}...")
    ms = (time.perf_counter() - t0) * 1000
    metrics.record("karpathy", ms=ms)
    logger.timing("karpathy", ms=ms, had_cot=refined.had_thought_tag, self_critique=self_critique)

    # ── 6. Council Review ─────────────────────────────────────────────────────
    final_output = refined.answer
    if not skip_council and council:
        _bar("PILLAR 6 · COUNCIL REVIEW  —  QA Gate")
        t0 = time.perf_counter()
        verdict = council.review(task=goal, output=refined.answer)
        print(verdict.report())
        results["verdict"] = verdict
        final_output = verdict.approved_output
        ms = (time.perf_counter() - t0) * 1000
        metrics.record("council_review", ms=ms, score=verdict.consensus_score, passed=verdict.passed)
        logger.timing("council", ms=ms, mode="review", score=verdict.consensus_score, passed=verdict.passed)

    # ── 7. LLM Wiki ──────────────────────────────────────────────────────────
    if not skip_wiki:
        _bar("PILLAR 7 · LLM WIKI  —  Knowledge Graph Ingest")
        t0 = time.perf_counter()
        wiki = LLMWiki(client, config=cfg.get("wiki"))
        page = wiki.ingest(raw_text=final_output, topic_hint=goal[:100])
        print(f"  ✓  Saved: wiki/{page.filename}  [{page.page_type}]  tags={page.tags}")
        results["wiki_page"] = page
        ms = (time.perf_counter() - t0) * 1000
        metrics.record("wiki", ms=ms)
        logger.timing("wiki", ms=ms, page_type=page.page_type)

    _bar("FINAL OUTPUT")
    print(final_output)

    logger.info("system", "workflow_complete", goal=goal[:80])

    # Webhook delivery
    if webhook_url:
        _bar("WEBHOOK  —  Delivering result")
        payload = {
            "goal": goal,
            "output": final_output[:4000],
            "verdict": {
                "score": results["verdict"].consensus_score if results.get("verdict") else None,
                "passed": results["verdict"].passed if results.get("verdict") else None,
            },
            "wiki_page": results["wiki_page"].filename if results.get("wiki_page") else None,
            "trace_id": logger.trace_id,
        }
        _fire_webhook(webhook_url, payload)
        print(f"  ✓  Webhook delivered to {webhook_url}")

    return results


def main() -> None:
    p = argparse.ArgumentParser(description="m1frame — Portable Multi-Agent Workflow")
    p.add_argument("--goal", required=True, help="High-level goal to accomplish")
    p.add_argument("--backend", default=None,
                   help="LLM backend: claude|openai|ollama|vllm|lmstudio")
    p.add_argument("--no-council",      action="store_true", help="Skip Council steps")
    p.add_argument("--no-wiki",         action="store_true", help="Skip Wiki ingest")
    p.add_argument("--no-openplanter",  action="store_true", help="Skip OpenPlanter investigation")
    p.add_argument("--quiet",           action="store_true", help="Minimal output")
    p.add_argument("--stream",          action="store_true", help="Stream Karpathy tokens to stdout")
    p.add_argument("--parallel",        action="store_true", help="Run independent Miras stories in parallel")
    p.add_argument("--self-critique",   action="store_true", help="Use Karpathy self-critique loop")
    p.add_argument("--webhook",         default=None, metavar="URL", help="POST result to this URL on completion")
    p.add_argument("--metrics-port",    type=int, default=None, metavar="PORT",
                   help="Expose Prometheus /metrics on this port")
    args = p.parse_args()
    run_workflow(
        goal=args.goal,
        backend=args.backend,
        skip_council=args.no_council,
        skip_wiki=args.no_wiki,
        skip_openplanter=args.no_openplanter,
        verbose=not args.quiet,
        stream=args.stream,
        parallel=args.parallel,
        self_critique=args.self_critique,
        webhook_url=args.webhook,
        metrics_port=args.metrics_port,
    )

if __name__ == "__main__":
    main()
