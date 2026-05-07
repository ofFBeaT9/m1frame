# m1frame

[![CI](https://github.com/mahdadshakiba/m1frame/actions/workflows/ci.yml/badge.svg)](https://github.com/mahdadshakiba/m1frame/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

**Portable multi-agent AI framework** — 7 pillars, 6 source repositories, one pipeline.  
Works with Claude, OpenAI, Ollama, vLLM, and LM Studio. Switch backends in one line.  
Fully offline-capable. Git-versionable. Zero lock-in.

---

## Source Repositories

| Pillar | Source | Role |
|---|---|---|
| **BMAD** | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Agile story backlog — analyst / architect / dev / qa / pm / investigator roles |
| **LLM Council** | [gcpdev/llm-council-skill](https://github.com/gcpdev/llm-council-skill) | Brainstorm before generation + QA review after |
| **Miras** | [ofFBeaT9/miras](https://github.com/ofFBeaT9/miras) | Sequential sub-agent orchestration with full state handoffs |
| **Karpathy Patterns** | [karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Forced `<thought>` chain-of-thought, deterministic prompting |
| **LLM Wiki** | [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) | Persistent three-layer knowledge graph (Analysis→Generation) |
| **OpenPlanter** | [ShinMegamiBoson/OpenPlanter](https://github.com/ShinMegamiBoson/OpenPlanter) | Recursive investigation agent — entity resolution, cross-referencing, dataset ingestion |

---

## Quick Start

```bash
git clone https://github.com/ofFBeaT9/m1frame.git && cd m1frame
pip install -r requirements.txt
cp .env.example .env           # add your ANTHROPIC_API_KEY
python scripts/qa_validate.py  # 43 tests, no key needed
python -m m1frame --goal "Build a FastAPI service with JWT auth"
```

Or with Make:
```bash
make install && make qa
make run GOAL="Investigate vendor payments against lobbying disclosures"
```

---

## 7-Pillar Pipeline

```
Your Goal
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. BMAD  —  Story Backlog                                   │
│    Scrum Master → ordered stories with roles + AC           │
│    Roles: analyst · architect · dev · qa · pm · investigator│
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Council Brainstorm  (PRE-generation)                     │
│    Critic · Advocate · Domain Expert analyse the goal       │
│    Synthesiser → unified implementation plan + risks        │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. OpenPlanter  —  Investigation Layer                      │
│    Auto-invoked for "investigator" stories                  │
│    Entity resolution · cross-referencing · dataset ingestion│
│    19-tool suite: file I/O, shell, web search, sub-agents   │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Miras  —  Multi-Agent Execution                          │
│    Each story → role-matched sub-agent                      │
│    Full AgentState passed between every handoff             │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Karpathy  —  Chain-of-Thought Refinement                 │
│    Forced <thought> reasoning · two-pass refine             │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Council Review  (POST-generation QA gate)                │
│    Consensus score ≥ 7/10 → approved_output                 │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. LLM Wiki  —  Knowledge Graph                             │
│    Analysis → Generation → interlinked Markdown pages       │
│    entities/ · concepts/ · sources/ · synthesis/            │
└─────────────────────────────────────────────────────────────┘
```

---

## OpenPlanter — Investigation Layer

OpenPlanter is a recursive investigation agent that ingests heterogeneous datasets, resolves entities across them, and surfaces non-obvious connections. In m1frame it runs as Pillar 3 and as a Miras sub-agent for stories with `role: investigator`.

```python
from agents.openplanter import OpenPlanterAgent

op = OpenPlanterAgent(llm_client, workspace="./workspace")

# Full investigation
result = op.investigate("Cross-reference vendor payments against lobbying disclosures")
print(result.report())

# Entity resolution across raw data
entities = op.resolve_entities("Acme Corp paid ACME Inc $500k in Q1 2025")

# Cross-reference two datasets
result = op.cross_reference(dataset_a="vendor_payments.csv", dataset_b="lobbying_db.csv")
```

Supported providers: `anthropic` · `openai` · `openrouter` · `cerebras`  
Optional service keys: `EXA_API_KEY` (web search) · `VOYAGE_API_KEY` (embeddings)

For full 19-tool support, install OpenPlanter directly:
```bash
pip install git+https://github.com/ShinMegamiBoson/OpenPlanter.git
```
Without it, m1frame runs OpenPlanter in **LLM-only mode** (all reasoning, no real file/shell tools).

---

## Switch Backends — One Line

```yaml
# config.yaml
backend: ollama     # claude | openai | ollama | vllm | lmstudio
```

```bash
python -m m1frame --goal "..." --backend ollama  # fully offline with Ollama
```

---

## Wiki — Three-Layer Architecture

```
wiki/raw/sources/   ← Immutable. You write here. LLM reads only.
wiki/               ← LLM-maintained pages (entities/ concepts/ sources/ synthesis/)
CLAUDE.md           ← Schema: page types, WikiLink conventions, ingest protocol
purpose.md          ← Goals, scope, evolving thesis — the wiki's soul
```

```python
wiki = LLMWiki(client)
wiki.ingest("raw text", topic_hint="topic")   # two-step Analysis→Generation
wiki.query("What connections exist between X and Y?")
wiki.lint()    # health check → LintReport (contradictions, orphans, gaps)
```

---

## QA

```bash
make qa                                         # all 43 tests
python scripts/qa_validate.py --pillar openplanter
python scripts/qa_validate.py --pillar e2e      # full 7-pillar pipeline
```

---

## File Map

```
m1frame/
├── purpose.md              ← Wiki soul
├── CLAUDE.md               ← Wiki schema
├── config.yaml             ← All config — one line to switch backends
├── llm_client.py           ← Unified adapter: Claude / OpenAI-compat / local
├── pyproject.toml          ← Installable: pip install m1frame
├── Makefile                ← make qa · make lint · make run GOAL="..."
├── LICENSE · CONTRIBUTING.md · SECURITY.md · CHANGELOG.md
├── .github/
│   ├── workflows/ci.yml    ← Matrix CI: Ubuntu/macOS/Windows × Py 3.10-3.12
│   ├── ISSUE_TEMPLATE/     ← Bug report + Feature request templates
│   └── pull_request_template.md
├── agents/
│   ├── bmad.py             ← BMADAgent, Blueprint, Story, BMAD_ROLES
│   ├── miras.py            ← MirasOrchestrator, AgentState, ROLE_MAP
│   ├── karpathy.py         ← KarpathyEngine, KarpathyResult
│   ├── council.py          ← LLMCouncil, BrainstormResult, CouncilVerdict
│   ├── wiki.py             ← LLMWiki, WikiPage, LintReport
│   └── openplanter.py      ← OpenPlanterAgent, InvestigationResult, Entity
├── wiki/                   ← Auto-created knowledge graph
└── scripts/
    ├── run_workflow.py     ← 7-pillar runner
    └── qa_validate.py      ← 43-test offline QA suite
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Report security issues via [SECURITY.md](SECURITY.md).

---

*m1frame v1.0.0 — Mahdad Shakiba, May 2026*
