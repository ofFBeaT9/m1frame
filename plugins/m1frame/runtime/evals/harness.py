"""Evaluation harness: does the full m1frame pipeline beat one strong model call?

For each problem it produces two answers:
  baseline  one direct call to a model (the "just ask GPT/Claude" alternative)
  m1frame   the full pipeline (planning, council, investigation, sub-agents, QA gate)

A judge model grades both answers blind, twice with the positions swapped; a
win counts only when both orderings agree, which cancels the judge's position
bias. Use a judge from a different provider than the systems under test, or
the judge may favour its own style; the report flags it when they match.

It also writes a blind sheet for human experts (answers shuffled as X/Y, key in
a separate file), because a model judging models is a screening step, not proof.

Outputs go to runs/evals/<eval_id>/: results.json, report.md, blind_sheet.csv, key.json.
"""
from __future__ import annotations

import csv
import datetime
import json
import random
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

CRITERIA = ("correctness", "completeness", "reasoning", "actionability", "risk_awareness")

BASELINE_SYSTEM = ("You are a senior expert. Answer the request thoroughly and accurately. "
                   "State assumptions, risks and a clear recommendation.")

JUDGE_SYSTEM = """You are an impartial expert grader. Two answers (A and B) respond to the same
request. Grade each from 1 to 10 on: correctness (factual and logical accuracy), completeness
(covers what the request needs), reasoning (sound, well-supported argument), actionability
(clear, usable recommendation or next steps), risk_awareness (identifies real risks and limits).
Do not reward length for its own sake. Penalise unsupported claims and invented facts.
Return ONLY JSON:
{"A": {"correctness": n, "completeness": n, "reasoning": n, "actionability": n, "risk_awareness": n},
 "B": {"correctness": n, "completeness": n, "reasoning": n, "actionability": n, "risk_awareness": n},
 "winner": "A" | "B" | "tie", "rationale": "one or two sentences"}"""


@dataclass
class Problem:
    id: str
    prompt: str
    domain: str = "general"
    rubric: str = ""


@dataclass
class SystemAnswer:
    text: str
    seconds: float
    model_requests: int | None = None
    approved: bool | None = None
    council_score: float | None = None
    error: str | None = None


@dataclass
class Judgement:
    winner: str                       # "m1frame" | "baseline" | "tie"
    consistent: bool                  # both orderings agreed
    scores: dict = field(default_factory=dict)   # {"m1frame": {...}, "baseline": {...}}
    rationales: list = field(default_factory=list)
    error: str | None = None


@dataclass
class ProblemResult:
    problem: Problem
    baseline: SystemAnswer
    m1frame: SystemAnswer
    judgement: Judgement


# ── Problems ──────────────────────────────────────────────────────────────────

def load_problems(path: str | Path) -> list[Problem]:
    import yaml
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    items = data.get("problems", []) if isinstance(data, dict) else data
    problems = []
    for i, item in enumerate(items):
        if not isinstance(item, dict) or not str(item.get("prompt", "")).strip():
            raise ValueError(f"problem #{i + 1} needs a non-empty 'prompt'")
        problems.append(Problem(id=str(item.get("id") or f"p{i + 1}"), prompt=str(item["prompt"]).strip(),
                                domain=str(item.get("domain", "general")), rubric=str(item.get("rubric", ""))))
    ids = [p.id for p in problems]
    if len(ids) != len(set(ids)):
        raise ValueError("problem ids must be unique")
    return problems


# ── Systems under test ────────────────────────────────────────────────────────

def baseline_answer(llm, problem: Problem) -> SystemAnswer:
    t0 = time.time()
    try:
        text = llm.chat(prompt=problem.prompt, system=BASELINE_SYSTEM, temperature=0.2)
        return SystemAnswer(text=text, seconds=round(time.time() - t0, 1), model_requests=1)
    except Exception as exc:  # noqa: BLE001 — record, keep evaluating
        return SystemAnswer(text="", seconds=round(time.time() - t0, 1), error=str(exc)[:300])


def m1frame_answer(problem: Problem, backend: str | None = None, isolate: bool = True) -> SystemAnswer:
    """Full pipeline. `isolate` skips wiki writes and skill learning, so earlier
    problems can't leak into later ones (measure the pipeline, not its memory)."""
    from scripts.run_workflow import run_workflow
    t0 = time.time()
    try:
        res = run_workflow(goal=problem.prompt, backend=backend, verbose=False,
                           skip_wiki=isolate, learn_skills=not isolate)
        verdict = res.get("verdict")
        return SystemAnswer(text=res.get("output") or "", seconds=round(time.time() - t0, 1),
                            model_requests=(res.get("usage") or {}).get("model_requests"),
                            approved=res.get("approved"),
                            council_score=getattr(verdict, "consensus_score", None))
    except Exception as exc:  # noqa: BLE001
        return SystemAnswer(text="", seconds=round(time.time() - t0, 1), error=str(exc)[:300])


# ── Judging ───────────────────────────────────────────────────────────────────

def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw or "", re.S)
    if not match:
        raise ValueError("judge returned no JSON")
    data = json.loads(match.group(0), strict=False)
    for side in ("A", "B"):
        data[side] = {c: max(1.0, min(10.0, float(data[side][c]))) for c in CRITERIA}
    if data.get("winner") not in {"A", "B", "tie"}:
        raise ValueError("judge winner must be A, B or tie")
    return data


def judge(judge_llm, problem: Problem, m1frame_text: str, baseline_text: str) -> Judgement:
    """Two blind passes with swapped positions; a win needs both to agree."""
    passes: list[dict] = []
    for m1frame_first in (True, False):
        a, b = (m1frame_text, baseline_text) if m1frame_first else (baseline_text, m1frame_text)
        prompt = (f"Request:\n{problem.prompt}\n\n"
                  + (f"Grading notes:\n{problem.rubric}\n\n" if problem.rubric else "")
                  + f"Answer A:\n{a}\n\nAnswer B:\n{b}")
        try:
            data = _parse(judge_llm.chat(prompt=prompt, system=JUDGE_SYSTEM, temperature=0.0))
        except Exception as exc:  # noqa: BLE001
            return Judgement(winner="tie", consistent=False, error=f"judge failed: {exc}"[:300])
        side = {"A": "m1frame" if m1frame_first else "baseline",
                "B": "baseline" if m1frame_first else "m1frame", "tie": "tie"}
        passes.append({"winner": side[data["winner"]],
                       "scores": {side["A"]: data["A"], side["B"]: data["B"]},
                       "rationale": str(data.get("rationale", ""))[:500]})
    winners = [str(p["winner"]) for p in passes]
    agree = winners[0] == winners[1]
    scores = {name: {c: round((passes[0]["scores"][name][c] + passes[1]["scores"][name][c]) / 2, 2)
                     for c in CRITERIA} for name in ("m1frame", "baseline")}
    return Judgement(winner=winners[0] if agree else "tie", consistent=agree,
                     scores=scores, rationales=[p["rationale"] for p in passes])


# ── Run + report ──────────────────────────────────────────────────────────────

def summarize(results: list[ProblemResult]) -> dict:
    judged = [r for r in results if not r.judgement.error and not r.m1frame.error and not r.baseline.error]
    wins = sum(r.judgement.winner == "m1frame" for r in judged)
    losses = sum(r.judgement.winner == "baseline" for r in judged)
    ties = len(judged) - wins - losses

    def mean(values):
        values = [v for v in values if v is not None]
        return round(sum(values) / len(values), 2) if values else None

    return {
        "problems": len(results), "judged": len(judged),
        "m1frame_wins": wins, "baseline_wins": losses, "ties": ties,
        "m1frame_win_rate": round(wins / len(judged), 3) if judged else None,
        "consistent_judgements": sum(r.judgement.consistent for r in judged),
        "mean_scores": {name: {c: mean(r.judgement.scores.get(name, {}).get(c) for r in judged)
                               for c in CRITERIA} for name in ("m1frame", "baseline")},
        "mean_seconds": {"m1frame": mean(r.m1frame.seconds for r in results),
                         "baseline": mean(r.baseline.seconds for r in results)},
        "mean_model_requests": {"m1frame": mean(r.m1frame.model_requests for r in results),
                                "baseline": mean(r.baseline.model_requests for r in results)},
        "m1frame_gate_passed": sum(r.m1frame.approved is True for r in results),
        "errors": sum(bool(r.m1frame.error or r.baseline.error or r.judgement.error) for r in results),
    }


def write_outputs(out_dir: Path, results: list[ProblemResult], meta: dict, seed: int = 0) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize(results)
    (out_dir / "results.json").write_text(json.dumps(
        {"meta": meta, "summary": summary, "results": [asdict(r) for r in results]},
        indent=2, default=str), encoding="utf-8")

    # Blind sheet for human experts: X/Y shuffled per problem, key kept separately.
    rng, key = random.Random(seed), {}
    with (out_dir / "blind_sheet.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["problem_id", "request", "answer_X", "answer_Y", "better (X/Y/tie)", "notes"])
        for r in results:
            x_is_m1 = rng.random() < 0.5
            key[r.problem.id] = {"X": "m1frame" if x_is_m1 else "baseline",
                                 "Y": "baseline" if x_is_m1 else "m1frame"}
            x, y = (r.m1frame.text, r.baseline.text) if x_is_m1 else (r.baseline.text, r.m1frame.text)
            w.writerow([r.problem.id, r.problem.prompt, x, y, "", ""])
    (out_dir / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(render_report(summary, results, meta), encoding="utf-8")
    return summary


def render_report(summary: dict, results: list[ProblemResult], meta: dict) -> str:
    s = summary
    rate = f"{s['m1frame_win_rate']:.0%}" if s["m1frame_win_rate"] is not None else "n/a"
    lines = [f"# m1frame evaluation {meta.get('eval_id', '')}", "",
             f"m1frame won {s['m1frame_wins']} of {s['judged']} judged problems ({rate}), "
             f"lost {s['baseline_wins']}, tied {s['ties']}.", "",
             f"- Systems: m1frame on `{meta.get('backend')}` vs a single call to `{meta.get('baseline')}`",
             f"- Judge: `{meta.get('judge')}`, two blind passes per problem, positions swapped; "
             f"{s['consistent_judgements']} of {s['judged']} judgements agreed across both passes",
             f"- Mean time: m1frame {s['mean_seconds']['m1frame']} s, baseline {s['mean_seconds']['baseline']} s",
             f"- Mean model calls: m1frame {s['mean_model_requests']['m1frame']}, "
             f"baseline {s['mean_model_requests']['baseline']}",
             f"- m1frame QA gate passed on {s['m1frame_gate_passed']} of {s['problems']} problems",
             f"- Errors: {s['errors']}", ""]
    if meta.get("judge_same_as_system"):
        lines += ["> Warning: the judge uses the same provider and model as a system under test, "
                  "so it may favour its own style. Re-run with a judge from another provider.", ""]
    lines += ["## Mean scores (1 to 10)", "", "| Criterion | m1frame | baseline |", "| --- | --- | --- |"]
    for c in CRITERIA:
        lines.append(f"| {c.replace('_', ' ')} | {s['mean_scores']['m1frame'][c]} | "
                     f"{s['mean_scores']['baseline'][c]} |")
    lines += ["", "## Per problem", "", "| Problem | Domain | Winner | Agreed | m1frame gate | Note |",
              "| --- | --- | --- | --- | --- | --- |"]
    for r in results:
        note = r.m1frame.error or r.baseline.error or r.judgement.error or (r.judgement.rationales or [""])[0]
        lines.append(f"| {r.problem.id} | {r.problem.domain} | {r.judgement.winner} | "
                     f"{'yes' if r.judgement.consistent else 'no'} | "
                     f"{'pass' if r.m1frame.approved else 'review' if r.m1frame.approved is False else '-'} | "
                     f"{str(note).replace('|', '/')[:160]} |")
    lines += ["", "A model judge screens; it doesn't prove. Before using these numbers in a pitch, have "
              "domain experts grade `blind_sheet.csv` (answers shuffled as X/Y; the key is in `key.json`)."]
    return "\n".join(lines) + "\n"


def run_eval(problems: list[Problem], *, baseline_llm, judge_llm, backend: str | None = None,
             out_root: str | Path = "runs/evals", isolate: bool = True,
             m1frame_fn: Callable[[Problem], SystemAnswer] | None = None,
             progress: Callable[[str], None] | None = None, seed: int = 0) -> tuple[Path, dict]:
    eval_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    out_dir = Path(out_root) / eval_id
    m1frame_fn = m1frame_fn or (lambda p: m1frame_answer(p, backend=backend, isolate=isolate))
    say = progress or (lambda _m: None)
    results = []
    for i, problem in enumerate(problems, 1):
        say(f"[{i}/{len(problems)}] {problem.id}: baseline")
        base = baseline_answer(baseline_llm, problem)
        say(f"[{i}/{len(problems)}] {problem.id}: m1frame pipeline")
        full = m1frame_fn(problem)
        if base.error or full.error:
            verdict = Judgement(winner="tie", consistent=False, error="not judged: a system failed")
        else:
            say(f"[{i}/{len(problems)}] {problem.id}: judging")
            verdict = judge(judge_llm, problem, full.text, base.text)
        results.append(ProblemResult(problem, base, full, verdict))
        write_outputs(out_dir, results, _meta(eval_id, backend, baseline_llm, judge_llm), seed)  # keep partials
    summary = write_outputs(out_dir, results, _meta(eval_id, backend, baseline_llm, judge_llm), seed)
    return out_dir, summary


def _describe(llm) -> str:
    backend = getattr(llm, "backend", "?")
    cfg = getattr(llm, "cfg", {}) or {}
    model = (cfg.get(backend) or {}).get("model") if isinstance(cfg, dict) else None
    return f"{backend}:{model}" if model else str(backend)


def _meta(eval_id, backend, baseline_llm, judge_llm) -> dict:
    return {"eval_id": eval_id, "backend": backend or _describe(baseline_llm).split(":")[0],
            "baseline": _describe(baseline_llm), "judge": _describe(judge_llm),
            "judge_same_as_system": _describe(judge_llm) == _describe(baseline_llm),
            "date": datetime.date.today().isoformat()}
