# Scientific Agent Skills integration audit

Audited on 2026-09-08, using Python 3.13.9 on Windows.

Source: [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills),
plugin version **2.66.0**, pinned commit
`9cf7d9aea7d84754db4c167ab04b299d33c444bc`. Upstream's root license is MIT;
individual skill metadata and bundled resources may specify additional attribution or licenses.

## Result

**All 163 skills are accessible through M1Frame. Full execution of all workflows is
not established.** This repository supplies Agent Skills: instructions, reference
material and supporting scripts. It does not supply 163 independently runnable
agents. Existing Miras agents consume the selected skills.

| Check | Result |
|---|---:|
| Downloaded skill and root metadata files verified against Git blob hashes | 2,053 |
| Discovered and parsed SKILL.md entries | 163 / 163 |
| Skill metadata/loading errors | 0 |
| Skills individually tested for complete prompt inclusion | 163 / 163 |
| Files within skill directories, including SKILL.md | 2,040 |
| Python scripts parsed without execution | 540 / 540 |
| Python syntax errors on Python 3.13 | 0 |
| Skills with at least one unresolved external Python import probe | 54 |
| Skills containing credential-name hints | 39 |
| Scientific workflows verified end to end against real services/data | 0 |

Import probing excludes Python's standard library and the skill's own script/package
names. The final missing-import count is 54 after excluding bundled local packages
such as `office` and `helpers`. Import availability does not establish compatible
versions, successful imports, native dependencies or working external services.
Imports may also be optional; this is an investigation aid, not a requirements lockfile.

The complete per-skill inventory, compatibility declarations, allowed-tool declarations,
import probes and credential-name presence flags are in [audit.json](audit.json).
No credential values are included. This snapshot describes the audited Python
environment, not every machine running M1Frame.

## Integration behavior

- `python -m scientific install` creates a pinned sparse checkout containing all
  skills and root metadata. A separate fresh-install test found all 163 skills.
- BMAD planning receives relevant complete instructions. Every Miras story selects
  instructions independently, in both sequential and parallel execution. Explicit
  `scientific.skills` selections override keyword selection.
- All skills are discoverable using `scientific_list`. `scientific_read` exposes
  complete instructions and supporting text with pagination; `scientific_resources`
  lists supporting files, including binary assets on disk. `scientific_audit` exposes
  dependency hints. These four tools use the existing HTTP and MCP tool registry.
- The catalog is separate from M1Frame's council-vetted learned-skill store.
  Missing checkouts preserve the core pipeline. `scientific.enabled: false`
  disables pipeline injection and tool catalog access.
- A default 60,000-character instruction budget prevents loading the full library
  into every prompt. Only complete instructions that fit are included. All 163
  skills fit individually at the audited revision; the selected list is reported
  in the workflow's `scientific` result.

## Execution boundaries

M1Frame's ordinary `LLMClient.chat` story calls do not execute arbitrary skill
scripts or add a tool loop. They receive scientific workflow instructions.
A tool-capable host can discover/read resources and execute applicable scripts
with its own tools, after satisfying the workflow's dependencies. The module does
not install the upstream development/scanner environment or all scientific packages.

Workflow-specific checks remain necessary for Python/R packages, executables,
system libraries, GPU/model requirements, licensed software, datasets, credentials
and live service access. The upstream repository's development project requires
Python 3.13; individual skills have their own compatibility declarations. The
M1Frame reader retains M1Frame's Python 3.10+ compatibility.

## Verification

- Existing offline QA: **164 / 164 passed** with the full catalog installed.
- New scientific integration tests: **8 / 8 passed**, including full pipeline
  propagation to the planner and all three mocked Miras stories.
- Ruff: passed for the repository. Mypy: passed for `agents/`, `scientific/`
  and `llm_client.py`.
- All skill instructions read and individually injected without truncation;
  supporting text reads encountered no decoding failures.
- No live LLM calls, paid API calls or scientific workflow executions were used
  to produce these integration results.

Reproduce:

```bash
python -m scientific install   # fresh checkout only; existing destinations are preserved
python -m scientific list
python -m scientific audit --output scientific-audit.json
python -m unittest scripts.test_scientific
python scripts/qa_validate.py
```
