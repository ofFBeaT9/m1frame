# m1frame

> **Portable multi-agent AI framework** — built from 5 real open-source repositories.  
> Works with Claude, OpenAI, Ollama, vLLM, and LM Studio. Switch backends in one line.  
> Fully offline-capable. Git-versionable. Zero lock-in.

---

## What it is

m1frame wires together five proven AI patterns into a single portable pipeline:

| Pillar | Source | What it does |
|---|---|---|
| **BMAD** | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Decomposes your goal into an agile story backlog. Assigns roles: analyst, architect, dev, qa, scrum_master, pm |
| **LLM Council** | [gcpdev/llm-council-skill](https://github.com/gcpdev/llm-council-skill) | Critic + Advocate + Domain Expert brainstorm **before** generation, then QA-review **after** |
| **Miras** | [ofFBeaT9/miras](https://github.com/ofFBeaT9/miras) | Routes each story to a role-matched sub-agent. Full state passed between every handoff |
| **Karpathy Patterns** | [karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Forces `<thought>` chain-of-thought. Deterministic, minimalist prompting |
| **LLM Wiki** | [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) | Two-step Analysis→Generation ingest. Builds a persistent, interlinked Markdown knowledge graph |

---

## Quick start

```bash
# 1. Clone
git clone <your-repo> && cd m1frame

# 2. Install
pip install -r requirements.txt

# 3. Set API key
cp .env.example .env
# Edit .env → ANTHROPIC_API_KEY=sk-ant-...
source .env

# 4. Verify (no API key needed)
python scripts/qa_validate.py

# 5. Run
python scripts/run_workflow.py --goal "Build a FastAPI service with JWT auth"
# or
python -m m1frame --goal "Build a FastAPI service with JWT auth"
```

---

## Pipeline — correct order

```
Your goal
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 1. BMAD  —  Story Backlog                               │
│    Scrum Master breaks goal → ordered stories           │
│    Each story: role (analyst/architect/dev/qa) + AC     │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Council Brainstorm  (PRE-generation)                 │
│    Critic · Advocate · Domain Expert analyse the goal   │
│    Synthesiser → unified implementation plan            │
└───────────────────────┬─────────────────────────────────┘
                        │ plan + risks injected into context
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Miras  —  Multi-Agent Execution                      │
│    Each story → role-matched sub-agent                  │
│    Full AgentState passed between every handoff         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Karpathy  —  Chain-of-Thought Refinement             │
│    Forces <thought> reasoning before final answer       │
│    Two-pass: refine=True for final synthesis            │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Council Review  (POST-generation QA gate)            │
│    Same personas now review the output                  │
│    Consensus score ≥ 7/10 → approved_output             │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 6. LLM Wiki  —  Knowledge Graph                         │
│    Step 1: Analysis (find entities, connections)        │
│    Step 2: Generation (write interlinked MD pages)      │
│    Saves to: entities/ concepts/ sources/ synthesis/    │
└─────────────────────────────────────────────────────────┘
```

---

## Switch backends — one line

```yaml
# config.yaml
backend: ollama        # claude | openai | ollama | vllm | lmstudio
```

```bash
# Or at runtime:
python scripts/run_workflow.py --goal "..." --backend ollama

# Fully offline (no API key):
ollama pull llama3.2
# set backend: ollama in config.yaml
```

---

## Wiki — three-layer architecture (Karpathy)

```
wiki/raw/sources/   ← You write here. LLM reads only. Never modified.
wiki/               ← LLM writes here (entities/ concepts/ sources/ synthesis/)
CLAUDE.md           ← Schema: you and the LLM co-evolve this file
purpose.md          ← Goals, scope, evolving thesis. LLM reads on every op.
```

Wiki operations:
```python
wiki = LLMWiki(client)
wiki.ingest("raw text", topic_hint="topic")   # two-step Analysis→Generation
wiki.query("What is X?")                       # index-first lookup + synthesis
wiki.lint()                                    # health check → LintReport
```

---

## File map

```
m1frame/
├── purpose.md          ← Wiki soul — research goals and thesis
├── CLAUDE.md           ← Wiki schema — page types, conventions
├── config.yaml         ← All config. One line to switch backends.
├── llm_client.py       ← Unified adapter: Claude / OpenAI-compat / local
├── pyproject.toml      ← Installable Python package
├── requirements.txt
├── .env.example
├── CHANGELOG.md
├── agents/
│   ├── bmad.py         ← BMADAgent, Blueprint, Story, BMAD_ROLES
│   ├── miras.py        ← MirasOrchestrator, AgentState, ROLE_MAP
│   ├── karpathy.py     ← KarpathyEngine, KarpathyResult
│   ├── council.py      ← LLMCouncil, BrainstormResult, CouncilVerdict
│   └── wiki.py         ← LLMWiki, WikiPage, LintReport
├── wiki/               ← Auto-created knowledge graph
│   ├── index.md
│   ├── log.md
│   ├── overview.md
│   ├── raw/sources/
│   ├── entities/
│   ├── concepts/
│   ├── sources/
│   └── synthesis/
└── scripts/
    ├── run_workflow.py ← Main 6-step runner
    └── qa_validate.py  ← 34-test offline QA suite
```

---

## QA

```bash
python scripts/qa_validate.py                  # all 34 tests, no key needed
python scripts/qa_validate.py --pillar council # one pillar
python scripts/qa_validate.py --pillar e2e     # full pipeline
```

---

## Use the source repos directly

`requirements.txt` includes commented-out pip-installable GitHub URLs.
Uncomment any you want to use as importable libraries alongside m1frame:

```
git+https://github.com/bmad-code-org/BMAD-METHOD.git
git+https://github.com/nashsu/llm_wiki.git
git+https://github.com/gcpdev/llm-council-skill.git
git+https://github.com/ofFBeaT9/miras.git
```

---

*m1frame v1.0.0 — Mahdad Shakiba, May 2026*
#
