# Purpose — Central Guide for the LLM Wiki

**System Name:** Portable Multi-Agent Workflow  
**Author:** Mahdad Shakiba  
**Version:** 1.0.0  
**Date:** 2026-05-04

---

## Mission Statement

This system is a portable, hallucination-resistant, multi-agent AI workflow designed to produce
high-fidelity outputs for advanced research, coding, and logical execution environments.  
It is LLM-agnostic and runs with Claude (API), OpenAI-compatible endpoints, or fully offline
local inference servers (Ollama, vLLM, LM Studio).

---

## Five-Pillar Architecture

| Pillar | Role | Module |
|---|---|---|
| BMAD Method | Blueprint — context mapping & task decomposition | `agents/bmad.py` |
| Miras Framework | Orchestrator — sub-agent routing & state handoffs | `agents/miras.py` |
| Karpathy Patterns | Engine — deterministic prompting + chain-of-thought | `agents/karpathy.py` |
| LLM Council | QA Gate — multi-persona debate & consensus scoring | `agents/council.py` |
| LLM Wiki | Memory Layer — persistent interlinked knowledge graph | `agents/wiki.py` |

---

## Guiding Principles

1. **Portability first** — all state lives in plain Markdown + YAML; version-control with Git.
2. **Hallucination resistance** — every output passes the Council QA gate before finalisation.
3. **Determinism** — Karpathy patterns force explicit `<thought>` chains; temperature ≤ 0.3 for reasoning tasks.
4. **Offline-capable** — swap `backend: claude` → `backend: ollama` in `config.yaml`; zero other changes needed.
5. **Domain-agnostic** — BMAD task decomposition can target physics, code, writing, or any structured domain.

---

## Wiki Conventions

- Every wiki page uses YAML frontmatter (`title`, `tags`, `related`, `created`).
- Pages are linked with `[[PageName]]` notation and indexed in `wiki/index.md`.
- New knowledge is ingested in two steps: *Capture* → raw note, then *Refine* → structured page.
