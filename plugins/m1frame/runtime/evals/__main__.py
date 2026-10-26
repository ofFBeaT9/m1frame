"""python -m evals — compare the full m1frame pipeline with a single model call.

  python -m evals run --problems evals/problems/starter.yaml
  python -m evals run --problems my.yaml --backend openrouter --judge-backend openai --limit 5
  python -m evals report runs/evals/<eval_id>      # print an existing report

Use a judge from a different provider than the systems under test (--judge-backend).
Each problem costs one baseline call, a full pipeline run (15-20 calls) and two judge calls.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="python -m evals", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run an evaluation")
    r.add_argument("--problems", default="evals/problems/starter.yaml")
    r.add_argument("--backend", default=None, help="backend for m1frame and the baseline (default: config)")
    r.add_argument("--baseline-model", default=None, help="model for the single-call baseline")
    r.add_argument("--judge-backend", default=None, help="judge provider (use a different one!)")
    r.add_argument("--judge-model", default=None)
    r.add_argument("--limit", type=int, default=None, help="only the first N problems")
    r.add_argument("--keep-memory", action="store_true",
                   help="let runs write the wiki and learn skills (default: isolated)")
    r.add_argument("--out", default="runs/evals")
    rep = sub.add_parser("report", help="print the report of a finished evaluation")
    rep.add_argument("path")
    a = p.parse_args(argv)

    if a.cmd == "report":
        print((Path(a.path) / "report.md").read_text(encoding="utf-8"))
        return

    from evals.harness import load_problems, run_eval
    from llm_client import LLMClient

    problems = load_problems(a.problems)[: a.limit or None]
    baseline = LLMClient(override_backend=a.backend)
    if a.baseline_model:
        baseline.cfg.setdefault(baseline.backend, {})["model"] = a.baseline_model
    judge = LLMClient(override_backend=a.judge_backend or a.backend)
    if a.judge_model:
        judge.cfg.setdefault(judge.backend, {})["model"] = a.judge_model
    print(f"Evaluating {len(problems)} problems: m1frame vs one call, judged by "
          f"{judge.backend}:{judge.cfg.get(judge.backend, {}).get('model')}", file=sys.stderr)
    out_dir, summary = run_eval(problems, baseline_llm=baseline, judge_llm=judge, backend=a.backend,
                                out_root=a.out, isolate=not a.keep_memory,
                                progress=lambda m: print(m, file=sys.stderr))
    print((out_dir / "report.md").read_text(encoding="utf-8"))
    print(f"Saved to {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
