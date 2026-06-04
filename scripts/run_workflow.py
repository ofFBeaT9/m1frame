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
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.bmad import BMADAgent
from agents.council import LLMCouncil
from agents.karpathy import KarpathyEngine
from agents.logger import PillarLogger
from agents.metrics import get_metrics
from agents.miras import MirasOrchestrator
from agents.openplanter import OpenPlanterAgent
from agents.skills import SkillLibrary
from agents.wiki import LLMWiki
from llm_client import LLMClient, load_config


def _bar(text: str) -> None:
    print(f"\n{'═'*62}\n  {text}\n{'═'*62}")

def _step(label: str, detail: str = "") -> None:
    print(f"\n  ▶  {label}")
    if detail:
        print(f"     {detail}")


def _fire_webhook(url: str, payload: dict) -> None:
    """POST result payload to webhook URL — non-fatal."""
    try:
        import json
        import urllib.request
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
    emit: Callable[..., None] | None = None,
    learn_skills: bool = True,
) -> dict:
    # `emit(type, pillar=..., **data)` streams progress to the Studio UI.
    # Default no-op ⇒ byte-identical CLI behaviour and the QA suite is unaffected.
    if emit is None:
        def emit(*_a, **_k):  # type: ignore[misc]
            return None

    cfg = load_config()
    client = LLMClient(override_backend=backend)
    purpose = Path("purpose.md").read_text() if Path("purpose.md").exists() else ""
    logger = PillarLogger()
    metrics = get_metrics()
    emit("run_start", goal=goal, options={
        "backend": backend or cfg.get("backend"),
        "parallel": parallel, "self_critique": self_critique,
        "skip_council": skip_council, "skip_wiki": skip_wiki,
        "skip_openplanter": skip_openplanter,
    })
    _t_run = time.perf_counter()

    if metrics_port:
        metrics.expose_http(port=metrics_port)
        print(f"  📊  Prometheus metrics at http://localhost:{metrics_port}/metrics")

    results: dict = {
        "goal": goal, "blueprint": None, "brainstorm": None,
        "investigation": None, "state": None, "verdict": None, "wiki_page": None,
    }

    # ── Skill recall (self-improving): seed planning with prior VETTED approaches ──
    # Defensive throughout: the learning loop must never be able to break a run.
    skills = None
    skill_ctx = ""
    try:
        skills = SkillLibrary(threshold=float((cfg.get("council") or {}).get("consensus_threshold", 7.0)))
        suggested = skills.suggest(goal)
        skill_ctx = skills.as_context(suggested)
        if suggested:
            emit("skill_suggested", pillar="bmad",
                 skills=[{"id": s.id, "title": s.title, "uses": s.uses, "score": s.score}
                         for s in suggested])
            if verbose:
                print(f"  ↻ recalled {len(suggested)} prior vetted skill(s) to seed planning")
    except Exception as e:  # noqa: BLE001 — recall is best-effort
        logger.warn("bmad", "skill_recall_error", error=str(e))

    # ── 1. BMAD — Story Backlog ───────────────────────────────────────────────
    _bar("PILLAR 1 · BMAD  —  Story Backlog")
    emit("pillar_start", pillar="bmad", idx=1, label="BMAD · Story Backlog")
    t0 = time.perf_counter()
    bmad = BMADAgent(client, config=cfg.get("bmad"))
    blueprint = bmad.plan(goal, extra_context="\n\n".join(filter(None, [purpose[:400], skill_ctx])))
    issues = bmad.validate(blueprint)
    print(f"  {'✓ Blueprint valid' if not issues else '⚠  ' + str(issues)}")
    if verbose:
        print(blueprint.summary())
    results["blueprint"] = blueprint
    emit("bmad_blueprint", pillar="bmad",
         project=blueprint.project_name, domain=blueprint.domain,
         mvp=blueprint.mvp_scope, issues=issues,
         stories=[{"id": s.id, "title": s.title, "role": s.role,
                   "complexity": s.complexity, "depends_on": s.depends_on,
                   "acceptance_criteria": s.acceptance_criteria[:3]}
                  for s in blueprint.stories])
    ms = (time.perf_counter() - t0) * 1000
    metrics.record("bmad", ms=ms)
    logger.timing("bmad", ms=ms, stories=len(blueprint.stories))
    emit("pillar_done", pillar="bmad", ms=round(ms))

    # Stream the council debate persona-by-persona to the Studio.
    def _on_persona_start(mode, persona):
        emit("council_persona_start", pillar="council", mode=mode, persona=persona)

    def _on_persona_done(mode, persona, payload):
        emit("council_persona", pillar="council", mode=mode, persona=persona, **payload)

    # ── 2. Council Brainstorm ─────────────────────────────────────────────────
    brainstorm_context = ""
    council = None
    if not skip_council:
        _bar("PILLAR 2 · COUNCIL BRAINSTORM  —  Pre-Generation")
        emit("pillar_start", pillar="council", idx=2, label="Council · Brainstorm")
        t0 = time.perf_counter()
        council = LLMCouncil(client, config=cfg.get("council"))
        brainstorm = council.brainstorm(
            task=goal, on_persona_start=_on_persona_start, on_persona_done=_on_persona_done,
        )
        print(brainstorm.summary())
        results["brainstorm"] = brainstorm
        emit("council_brainstorm", pillar="council",
             plan=brainstorm.recommended_plan,
             steps=brainstorm.implementation_steps,
             risks=brainstorm.risks_to_mitigate,
             confidence=brainstorm.confidence)
        brainstorm_context = (
            f"Council plan: {brainstorm.recommended_plan}\n"
            + "\n".join(f"- {s}" for s in brainstorm.implementation_steps)
            + "\nRisks: " + "; ".join(brainstorm.risks_to_mitigate)
        )
        ms = (time.perf_counter() - t0) * 1000
        metrics.record("council_brainstorm", ms=ms)
        logger.timing("council", ms=ms, mode="brainstorm", confidence=brainstorm.confidence)
        emit("pillar_done", pillar="council", ms=round(ms), phase="brainstorm")

    # ── 3. OpenPlanter — Investigation Pass ───────────────────────────────────
    investigation_context = ""
    has_investigator_stories = any(
        getattr(s, "role", "") == "investigator" for s in blueprint.stories
    )
    if not skip_openplanter and has_investigator_stories:
        _bar("PILLAR 3 · OPENPLANTER  —  Investigation")
        emit("pillar_start", pillar="openplanter", idx=3, label="OpenPlanter · Investigation")
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
        emit("openplanter_result", pillar="openplanter", mode=planter.mode,
             summary=inv_result.summary[:600], web_results=len(inv_result.web_results))
        emit("pillar_done", pillar="openplanter", ms=round(ms))
    elif not skip_openplanter:
        _bar("PILLAR 3 · OPENPLANTER  —  Skipped (no investigator stories)")
        emit("pillar_skipped", pillar="openplanter", idx=3,
             reason="no investigator stories")

    # ── 4. Miras — Execute Stories ────────────────────────────────────────────
    _bar("PILLAR 4 · MIRAS  —  Multi-Agent Execution" + (" (parallel)" if parallel else ""))
    emit("pillar_start", pillar="miras", idx=4,
         label="Miras · Multi-Agent Execution" + (" (parallel)" if parallel else ""))

    def on_start(story):
        _step(f"[{story.role.upper()}] Story {story.id}: {story.title}")
        emit("story_start", pillar="miras", id=story.id, role=story.role, title=story.title)

    def on_done(story, result):
        print(f"     ✓  {result[:100].replace(chr(10),' ')}...")
        emit("story_done", pillar="miras", id=story.id, role=story.role,
             preview=result[:200].replace(chr(10), " "))

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
    emit("pillar_done", pillar="miras", ms=round(ms), stories_done=len(state.outputs))

    # ── 5. Karpathy — Refinement ──────────────────────────────────────────────
    _bar("PILLAR 5 · KARPATHY  —  Chain-of-Thought Refinement" + (" + Self-Critique" if self_critique else ""))
    emit("pillar_start", pillar="karpathy", idx=5,
         label="Karpathy · Chain-of-Thought Refinement")
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
            emit("karpathy_token", pillar="karpathy", chunk=chunk)
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
    emit("karpathy_done", pillar="karpathy", had_cot=refined.had_thought_tag,
         thought=refined.thought[:1200], answer_preview=refined.answer[:400])
    emit("pillar_done", pillar="karpathy", ms=round(ms))

    # ── 6. Council Review ─────────────────────────────────────────────────────
    final_output = refined.answer
    if not skip_council and council:
        _bar("PILLAR 6 · COUNCIL REVIEW  —  QA Gate")
        emit("pillar_start", pillar="council", idx=6, label="Council · QA Gate Review")
        t0 = time.perf_counter()
        verdict = council.review(
            task=goal, output=refined.answer,
            on_persona_start=_on_persona_start, on_persona_done=_on_persona_done,
        )
        print(verdict.report())
        results["verdict"] = verdict
        final_output = verdict.approved_output
        ms = (time.perf_counter() - t0) * 1000
        metrics.record("council_review", ms=ms)   # score/passed are logged + emitted below, not metrics fields
        logger.timing("council", ms=ms, mode="review", score=verdict.consensus_score, passed=verdict.passed)
        emit("council_verdict", pillar="council",
             score=verdict.consensus_score, verdict=verdict.verdict,
             passed=verdict.passed, summary=verdict.summary,
             required_fixes=verdict.required_fixes)
        emit("qa_gate", pillar="council", gate="results-review",
             status="PASS" if verdict.passed else "CONCERNS",
             score=verdict.consensus_score)
        emit("pillar_done", pillar="council", ms=round(ms), phase="review")

        # ── Skill learning (vetted): remember HOW, only when the council passed ──
        if learn_skills and skills is not None and verdict.passed:
            try:
                learned = skills.learn(goal, blueprint, verdict.consensus_score,
                                       approach=(refined.answer[:200] if refined.answer else ""))
                if learned:
                    emit("skill_learned", pillar="council", id=learned.id, title=learned.title,
                         score=learned.score, uses=learned.uses)
                    results["skill"] = learned
                    if verbose:
                        print(f"  ★ learned vetted skill: {learned.title} ({learned.score:.1f}/10)")
            except Exception as e:  # noqa: BLE001 — learning is best-effort, never fatal
                logger.warn("council", "skill_learn_error", error=str(e))

    # ── 7. LLM Wiki ──────────────────────────────────────────────────────────
    page = None
    if not skip_wiki:
        _bar("PILLAR 7 · LLM WIKI  —  Knowledge Graph Ingest")
        emit("pillar_start", pillar="wiki", idx=7, label="LLM Wiki · Knowledge Graph Ingest")
        t0 = time.perf_counter()
        wiki = LLMWiki(client, config=cfg.get("wiki"))
        page = wiki.ingest(raw_text=final_output, topic_hint=goal[:100])
        print(f"  ✓  Saved: wiki/{page.filename}  [{page.page_type}]  tags={page.tags}")
        results["wiki_page"] = page
        ms = (time.perf_counter() - t0) * 1000
        metrics.record("wiki", ms=ms)
        logger.timing("wiki", ms=ms, page_type=page.page_type)
        emit("wiki_page", pillar="wiki", title=page.title, page_type=page.page_type,
             filename=page.filename, tags=page.tags)
        emit("graph_delta", pillar="wiki",
             nodes=[{"id": page.title, "type": page.page_type}], links=[])
        emit("pillar_done", pillar="wiki", ms=round(ms))

    _bar("FINAL OUTPUT")
    print(final_output)

    logger.info("system", "workflow_complete", goal=goal[:80])
    emit("final", output=final_output[:8000],
         score=results["verdict"].consensus_score if results.get("verdict") else None,
         passed=results["verdict"].passed if results.get("verdict") else None,
         wiki_page=page.filename if page else None)
    emit("done", ms=round((time.perf_counter() - _t_run) * 1000))

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
                   help="LLM backend: claude|openai|openrouter|ollama|vllm|lmstudio")
    p.add_argument("--no-learn",        action="store_true",
                   help="Don't learn/recall a council-vetted skill")
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
        learn_skills=not args.no_learn,
    )

if __name__ == "__main__":
    main()
