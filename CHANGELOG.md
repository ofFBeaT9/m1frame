# Changelog — m1frame

## v1.0.0 — 2026-05-06

### Initial release

**Five pillars integrated from source repos:**
- BMAD Method (bmad-code-org/BMAD-METHOD) — agile story backlog with 6 role types
- LLM Council (gcpdev/llm-council-skill) — pre-gen brainstorm + post-gen QA review
- Miras (ofFBeaT9/miras) — sequential sub-agent orchestration with state handoffs
- Karpathy Patterns (karpathy gist) — forced `<thought>` CoT, deterministic prompting
- LLM Wiki (nashsu/llm_wiki) — three-layer persistent knowledge graph

**Features:**
- Single-line backend switching: Claude → Ollama → vLLM → LM Studio → OpenAI
- Fully offline-capable (Ollama backend, no API key needed)
- Git-versionable knowledge graph (pure Markdown + YAML)
- 35-test QA suite with offline mock (no API key required)
- `python -m m1frame --goal "..."` entry point
