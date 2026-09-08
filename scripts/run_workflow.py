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
import threading
import time
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.bmad import BMADAgent
from agents.council import LLMCouncil
from agents.guardrails import GuardrailEngine
from agents.karpathy import KarpathyEngine
from agents.logger import PillarLogger
from agents.metrics import get_metrics
from agents.miras import MirasOrchestrator
from agents.openplanter import OpenPlanterAgent
from agents.skills import SkillLibrary
from agents.wiki import LLMWiki
from llm_client import LLMClient, load_config


def _force_utf8() -> None:
    """Windows consoles default to cp1252; the pillar banners use box-drawing
    glyphs (═ ▶ ✓ ·). Force UTF-8 so piped/captured runs don't crash on encode.

    Called from `main()` *and* from `run_workflow()`, because the API server and
    the MCP server import and call `run_workflow` directly — they never go
    through `main()`, so guarding only the CLI left every programmatic caller
    one box-drawing character away from a UnicodeEncodeError.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001 — best-effort; never block a run
            pass


# Verbosity is per-run, and the API server can run workflows concurrently in
# threads — so this is thread-local rather than a module global.
_out_state = threading.local()


def _safe_print(*args, **kwargs) -> None:
    """print() that degrades instead of raising on an un-encodable console."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        clean = [str(a).encode(enc, "replace").decode(enc, "replace") for a in args]
        print(*clean, **kwargs)


def say(*args, **kwargs) -> None:
    """Console output that honours the run's `verbose` flag.

    `verbose=False` is what `api/server.py` and `mcp_server.py` pass to keep
    pillar banners out of their logs; before this, only 7 of 35 output sites
    actually checked it.
    """
    if getattr(_out_state, "verbose", True):
        _safe_print(*args, **kwargs)


def _bar(text: str) -> None:
    say(f"\n{'═'*62}\n  {text}\n{'═'*62}")

def _step(label: str, detail: str = "") -> None:
    say(f"\n  ▶  {label}")
    if detail:
        say(f"     {detail}")


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
        _safe_print(f"  ⚠  Webhook delivery failed: {exc}")


def run_workflow(
    goal: str,
    backend: str | None = None,
    skip_council: bool = False,
    skip_wiki: bool = False,
    skip_openplanter: bool = False,
    skip_guardrails: bool = False,
    verbose: bool = True,
    stream: bool = False,
    parallel: bool = False,
    self_critique: bool = False,
    webhook_url: str | None = None,
    metrics_port: int | None = None,
    emit: Callable[..., None] | None = None,
    learn_skills: bool = True,
) -> dict:
    # Protect every entry path, not just the CLI (see `_force_utf8`), and scope
    # this run's verbosity so `say()` can honour it at all 35 output sites.
    _force_utf8()
    _out_state.verbose = bool(verbose)

    # `emit(type, pillar=..., **data)` streams progress to the Studio UI.
    # Default no-op ⇒ byte-identical CLI behaviour and the QA suite is unaffected.
    if emit is None:
        def emit(*_a, **_k):  # type: ignore[misc]
            return None

    cfg = load_config()
    client = LLMClient(override_backend=backend)
    purpose = Path("purpose.md").read_text(encoding="utf-8") if Path("purpose.md").exists() else ""
    logger = PillarLogger()
    metrics = get_metrics()
    guard = GuardrailEngine(
        config=({"enabled": False} if skip_guardrails else cfg.get("guardrails")),
        logger=logger, emit=emit,
    )
    emit("run_start", goal=goal, options={
        "backend": backend or cfg.get("backend"),
        "parallel": parallel, "self_critique": self_critique,
        "skip_council": skip_council, "skip_wiki": skip_wiki,
        "skip_openplanter": skip_openplanter,
    })
    _t_run = time.perf_counter()

    if metrics_port:
        metrics.expose_http(port=metrics_port)
        say(f"  📊  Prometheus metrics at http://localhost:{metrics_port}/metrics")

    results: dict = {
        "goal": goal, "blueprint": None, "brainstorm": None,
        "investigation": None, "state": None, "verdict": None, "wiki_page": None,
    }

    # ── Guardrail · INPUT gate ────────────────────────────────────────────────
    # Screen the goal before any pillar runs; a block short-circuits the run.
    gin = guard.check_input(goal)
    emit("guardrail", pillar="guardrails", gate="input",
         status=gin.action.upper(), categories=gin.categories)
    if not gin.allowed:
        refusal = guard.refusal_text(gin)
        _bar("GUARDRAIL · INPUT BLOCKED")
        say(refusal)
        logger.warn("guardrails", "input_blocked", categories=gin.categories)
        results["blocked"] = True
        results["output"] = refusal
        emit("final", output=refusal, score=None, passed=False, blocked=True)
        emit("done", ms=round((time.perf_counter() - _t_run) * 1000))
        return results

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

    # External skills are reference material, kept separate from vetted recipes.
    scientific_library = None
    scientific_cfg = cfg.get("scientific") or {}
    scientific_ctx = ""
    if scientific_cfg.get("enabled", True):
        try:
            from scientific import ScientificLibrary
            scientific_library = ScientificLibrary(scientific_cfg.get("path"))
            scientific_ctx, selected = scientific_library.context(
                goal, names=scientific_cfg.get("skills"),
                max_chars=int(scientific_cfg.get("max_context_chars", 60000)))
            results["scientific"] = {"available": bool(scientific_library.skills),
                                     "catalog_count": len(scientific_library.skills),
                                     "selected": selected, "errors": scientific_library.errors}
            if selected:
                emit("scientific_selected", pillar="scientific", skills=selected)
        except Exception as exc:  # noqa: BLE001 — optional module must not break a run
            scientific_library = None
            scientific_ctx = ""
            logger.warn("scientific", "load_error", error=str(exc))
            results["scientific"] = {"available": False, "error": str(exc)}

    # ── 1. BMAD — Story Backlog ───────────────────────────────────────────────
    _bar("PILLAR 1 · BMAD  —  Story Backlog")
    emit("pillar_start", pillar="bmad", idx=1, label="BMAD · Story Backlog")
    t0 = time.perf_counter()
    bmad = BMADAgent(client, config=cfg.get("bmad"))
    blueprint = bmad.plan(goal, extra_context="\n\n".join(filter(None, [purpose[:400], skill_ctx, scientific_ctx])))
    issues = bmad.validate(blueprint)
    say(f"  {'✓ Blueprint valid' if not issues else '⚠  ' + str(issues)}")
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
        say(brainstorm.summary())
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
        say(f"  Mode: {planter.mode}")
        inv_result = planter.investigate(task=goal)
        say(inv_result.report())
        results["investigation"] = inv_result
        # ── Guardrail · INGEST gate ── (untrusted web/data: redact + quarantine,
        # never block — findings are data to analyse, not instructions to obey)
        ging = guard.check_ingest(inv_result.summary)
        if ging.action != "allow":
            emit("guardrail", pillar="guardrails", gate="ingest",
                 status=ging.action.upper(), categories=ging.categories)
        investigation_context = f"\nInvestigation findings:\n{ging.text}"
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
        say(f"     ✓  {result[:100].replace(chr(10),' ')}...")
        emit("story_done", pillar="miras", id=story.id, role=story.role,
             preview=result[:200].replace(chr(10), " "))

    t0 = time.perf_counter()
    miras = MirasOrchestrator(
        client, config=cfg.get("miras"),
        on_subtask_start=on_start, on_subtask_done=on_done,
        scientific_library=scientific_library, scientific_config=scientific_cfg,
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
        say("  ▶  Streaming Karpathy refinement...")
        chunks = []
        for chunk in client.stream(
            prompt=synthesis_prompt,
            system=engine.cfg.get("extra_system", purpose[:300]),
            temperature=engine.temperature,
        ):
            _safe_print(chunk, end="", flush=True)
            chunks.append(chunk)
            emit("karpathy_token", pillar="karpathy", chunk=chunk)
        _safe_print()
        full_raw = "".join(chunks)
        refined = engine._parse(full_raw)
    elif self_critique:
        refined = engine.self_critique(synthesis_prompt, extra_system=purpose[:300])
        say("  ✓  Self-critique complete")
    else:
        refined = engine.run(
            prompt=synthesis_prompt,
            extra_system=purpose[:300],
            refine=True,
        )

    say(f"  ✓  CoT extracted: {'yes' if refined.had_thought_tag else 'no'}")
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
        say(verdict.report())
        results["verdict"] = verdict
        final_output = verdict.approved_output
        ms = (time.perf_counter() - t0) * 1000
        metrics.record("council_review", ms=ms)   # score/passed are logged + emitted below, not metrics fields
        logger.timing("council", ms=ms, mode="review", score=verdict.consensus_score, passed=verdict.passed)
        emit("council_verdict", pillar="council",
             score=verdict.consensus_score, verdict=verdict.verdict,
             passed=verdict.passed, summary=verdict.summary,
             required_fixes=verdict.required_fixes)
        # ── Structural sensor: objective evidence beside the council's judgement ──
        # Advisory by default — the measurement is reported, the council's verdict
        # stands. Set sensors.enforce in config.yaml to give it veto power. Wholly
        # best-effort: a missing binary or a sensor error can never affect a run.
        gate_status = "PASS" if verdict.passed else "CONCERNS"
        try:
            from sensors.tools import client as _sensor_client
            from sensors.tools import gate as _sensor_gate
            from sensors.tools import sensor_config as _sensor_config
            if _sensor_config().get("enabled", True) and _sensor_client().available():
                _sr = _sensor_client().scan(".")
                _sv = _sensor_gate().fuse(verdict.consensus_score, _sr)
                emit("sensor_reading", pillar="council", sensor="sentrux",
                     structural_score=_sv.structural_score, verdict=_sv.verdict,
                     basis=_sv.basis, enforced=_sv.enforced)
                results["structural"] = _sv.to_dict()
                if _sv.enforced and _sv.verdict != "PASS" and verdict.passed:
                    # Opt-in veto, and it has to be a REAL one. Writing the fused
                    # result into a display string only would make `enforce: true`
                    # a label that changes nothing — worse than not offering it,
                    # because it advertises a safety mechanism that doesn't act.
                    # `passed` is what gates skill-learning here and what every
                    # caller (incl. mcp_server.m1frame_run) reads.
                    verdict.passed = False
                    verdict.required_fixes = list(verdict.required_fixes) + [
                        f"structural score {_sv.structural_score}/10 "
                        f"({_sv.verdict}) — sensor veto, sensors.enforce=true"]
                    results["structural_veto"] = True
                    logger.warn("council", "structural_veto",
                                structural=_sv.structural_score, verdict=_sv.verdict)
                    if verbose:
                        print(f"  ✗ STRUCTURAL VETO: {_sv.verdict} "
                              f"({_sv.structural_score}/10) overrides a passing council")
                if _sv.enforced:
                    gate_status = _sv.verdict
                if verbose and _sv.structural_score is not None:
                    print(f"  ◆ structural {_sv.structural_score:.3f}/10 "
                          f"({_sv.basis}, {'enforced' if _sv.enforced else 'advisory'})")
        except Exception as e:  # noqa: BLE001 — a sensor must never break a run
            logger.warn("council", "sensor_error", error=str(e))

        emit("qa_gate", pillar="council", gate="results-review",
             status=gate_status, score=verdict.consensus_score)
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
                    # Learning remembers what passed; optimisation makes it better.
                    # Runs automatically here so the loop is actually closed, scored
                    # on coverage of the goal's own keywords.
                    try:
                        import re as _re

                        from agents.skills import _keywords
                        from optimizers.tools import keyword_scorer, optimizer_config
                        if optimizer_config().get("enabled", True):
                            # Candidates must come from THIS run's own material.
                            # With only the optimiser's generic phrase pool, a scorer
                            # rewarding goal-specific terms can never be satisfied and
                            # every edit is rejected — optimisation that cannot succeed.
                            _src = f"{refined.answer or ''} {verdict.summary or ''}"
                            _pool = [s.strip() for s in _re.split(r"(?<=[.!?])\s+|\n+", _src)
                                     if 20 <= len(s.strip()) <= 300][:24]
                            _opt = skills.optimize_skill(
                                learned.id, keyword_scorer(_keywords(goal)[:6]),
                                rounds=int(optimizer_config().get("rounds", 12)),
                                pool=_pool or None)
                            if _opt.get("persisted"):
                                emit("skill_optimized", pillar="council", id=learned.id,
                                     tier=_opt.get("tier"), before=_opt.get("before_score"),
                                     after=_opt.get("after_score"))
                                if verbose:
                                    print(f"  ⟳ optimised skill ({_opt.get('tier')}): "
                                          f"{_opt.get('before_score'):.2f} → "
                                          f"{_opt.get('after_score'):.2f}")
                    except Exception as e:  # noqa: BLE001 — optimisation is best-effort
                        logger.warn("council", "skill_optimize_error", error=str(e))
            except Exception as e:  # noqa: BLE001 — learning is best-effort, never fatal
                logger.warn("council", "skill_learn_error", error=str(e))

    # ── 7. LLM Wiki ──────────────────────────────────────────────────────────
    # ── Guardrail · OUTPUT gate ───────────────────────────────────────────────
    # Redact PII/secrets from, or block, the final answer before it is printed
    # and ingested into the knowledge graph.
    gout = guard.check_output(final_output)
    emit("guardrail", pillar="guardrails", gate="output",
         status=gout.action.upper(), categories=gout.categories)
    if not gout.allowed:
        final_output = guard.refusal_text(gout)
        logger.warn("guardrails", "output_blocked", categories=gout.categories)
    else:
        final_output = gout.text

    page = None
    if not skip_wiki:
        _bar("PILLAR 7 · LLM WIKI  —  Knowledge Graph Ingest")
        emit("pillar_start", pillar="wiki", idx=7, label="LLM Wiki · Knowledge Graph Ingest")
        t0 = time.perf_counter()
        wiki = LLMWiki(client, config=cfg.get("wiki"))
        page = wiki.ingest(raw_text=final_output, topic_hint=goal[:100])
        say(f"  ✓  Saved: wiki/{page.filename}  [{page.page_type}]  tags={page.tags}")
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
    say(final_output)

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
        say(f"  ✓  Webhook delivered to {webhook_url}")

    return results


def main() -> None:
    _force_utf8()
    p = argparse.ArgumentParser(description="m1frame — Portable Multi-Agent Workflow")
    p.add_argument("--goal", required=True, help="High-level goal to accomplish")
    p.add_argument("--backend", default=None,
                   help="LLM backend: claude|openai|openrouter|ollama|vllm|lmstudio")
    p.add_argument("--no-learn",        action="store_true",
                   help="Don't learn/recall a council-vetted skill")
    p.add_argument("--no-council",      action="store_true", help="Skip Council steps")
    p.add_argument("--no-wiki",         action="store_true", help="Skip Wiki ingest")
    p.add_argument("--no-openplanter",  action="store_true", help="Skip OpenPlanter investigation")
    p.add_argument("--no-guardrails",   action="store_true", help="Skip the content-safety guardrail gates")
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
        skip_guardrails=args.no_guardrails,
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
