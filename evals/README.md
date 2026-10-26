# Evaluating m1frame

Does the full pipeline beat one strong model call? This harness answers that with numbers.

```bash
python -m evals run --problems evals/problems/starter.yaml --judge-backend openai
python -m evals run --problems my_problems.yaml --backend openrouter --judge-backend claude --limit 5
python -m evals report runs/evals/<eval_id>
```

For each problem it produces a **baseline** (one direct model call) and an **m1frame** answer
(the full pipeline), then a judge model grades both **blind, twice, with positions swapped**.
A win counts only when both passes agree, which cancels the judge's position bias.

Outputs in `runs/evals/<eval_id>/`:

| File | What it is |
|---|---|
| `report.md` | Win/tie/loss, mean scores per criterion, time and model calls per system |
| `results.json` | Everything, per problem |
| `blind_sheet.csv` | Both answers shuffled as X/Y for **human experts** to grade |
| `key.json` | Which of X/Y was m1frame (keep it away from the graders) |

Rules that keep the numbers honest:

- Use a judge from a **different provider** than the systems under test (`--judge-backend`);
  the report warns when they match.
- Runs are **isolated** by default (no wiki writes or skill learning between problems);
  `--keep-memory` measures the compounding knowledge base instead.
- A model judge screens; it doesn't prove. Before quoting results in a pitch, have domain
  experts grade `blind_sheet.csv`.
- `problems/starter.yaml` is a starting set. Results on a client's own problems are what count.

Cost: per problem, one baseline call, one full pipeline run (typically 15–20 calls) and two judge calls.
