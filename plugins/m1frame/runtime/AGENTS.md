# M1Frame repository operating instructions

For prompts in this repository, use M1Frame's available capabilities as part of
the work. Discover broadly, load selectively, and report actual execution.

## Start and recall

- At the start of a task, run `python -m scripts.context_probe --query "<task>"`
  or call `m1frame_context` if this repository's MCP server is connected. Reuse
  the inventory within a task unless configuration or installed skills change.
- Read `purpose.md` and navigate `wiki/index.md` before selecting relevant wiki
  pages. Consult prior decisions and contradictions before architectural changes.
- If host Miras tools are available, call `miras_get_context` or `miras_recall`
  for this task. If absent, use local wiki/learned recipes and state the limitation.
  Do not imply that local `agents/miras.py` is the external memory service.

## Skills, tools, and agents

- Discover learned recipes through `skill_search`/`skill_read`; discover installed
  scientific skills through `scientific_list`, then read applicable instructions
  and supporting resources with `scientific_read`/`scientific_resources`.
- Use relevant host skills as well. A catalog entry alone is not execution proof.
  Never load every full skill into context or install all scientific dependencies.
- For coding work, carry out planning, implementation, and independent checks with
  the host's actual file, shell, and testing tools. Use the analyst/architect/dev/QA
  roles to cover the task, scaled to its scope. Do not substitute generated code or
  a council score for running appropriate checks.
- For a requested full deliberation, use `m1frame_run` or
  `python scripts/run_workflow.py --goal "<goal>"` with the configured live backend.
  Never recursively call the workflow from within a workflow's own story call.
- Keep tool approval requirements. Do not auto-approve writes based on model output.
- After meaningful work, update appropriate project knowledge per `CLAUDE.md`;
  store verified decisions in host Miras when available and relevant. Avoid storing
  secrets, speculative claims, or claiming a subsystem ran when it did not.

## Context headroom and honesty

- Keep the current request, constraints, relevant sources, dependency deliverables,
  and test findings in context. Use bounded retrieval and explicit omissions.
- Inspect the `context` configuration and actual backend context window. The local
  headroom guard uses conservative estimates; it is not the external Headroom product.
  Use a host Headroom tool if available, otherwise say it is unavailable when relevant.
- Host tools, MCP connections, API credentials, optional packages, and model windows
  are separate from repository files. These instructions do not install or connect them.
- Full Studio chat is the default. Quick answer explicitly bypasses the workflow.

## Validation

Before committing runtime changes, run:

```
python scripts/qa_validate.py
python -m unittest scripts.test_scientific scripts.test_efficiency scripts.test_full_system
ruff check .
mypy agents/ llm_client.py --ignore-missing-imports
```

Report mock/offline results separately from live-provider or hardware verification.
Preserve unrelated work; only push or publish when requested.
