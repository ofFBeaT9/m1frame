# CLAUDE.md — Wiki Schema & Workflow Contract

> This file is co-evolved by the human and the LLM. It defines how the wiki works,
> what page types exist, and how agents should behave. Read this before any wiki operation.
> Based on Karpathy's LLM Wiki gist + nashsu/llm_wiki conventions.

---

## Page Types

| Type | Directory | Purpose |
|---|---|---|
| `source` | `wiki/sources/` | Summary of an ingested external source |
| `entity` | `wiki/entities/` | Named thing (person, project, tool, org) |
| `concept` | `wiki/concepts/` | Abstract idea, pattern, or method |
| `synthesis` | `wiki/synthesis/` | Cross-source insight or conclusion |
| `query` | `wiki/queries/` | Saved query and its answer |

---

## YAML Frontmatter Schema

Every wiki page must start with:

```yaml
---
title: Page Title
tags: [tag1, tag2]
related: ["[[Other Page]]", "[[Another]]"]
created: 2026-05-04
sources: ["source-slug"]        # for non-source pages
page_type: concept              # one of the types above
confidence: high                # high | medium | low
---
```

---

## WikiLink Conventions

- Internal links: `[[Page Title]]` — exact title, case-sensitive
- All mentioned entities/concepts with their own page MUST be linked
- `related:` in frontmatter mirrors body WikiLinks
- `wiki/index.md` is the navigation entry point — never bypass it

---

## Two-Step Ingest Protocol

All new knowledge goes through exactly two LLM passes:

**Step 1 — Analysis** (`ANALYSIS_SYSTEM` prompt):
- Identify key entities and concepts
- Find connections to existing pages
- Detect contradictions with existing knowledge
- Recommend page type and structure

**Step 2 — Generation** (`GENERATION_SYSTEM` prompt):
- Write the actual wiki page using the analysis
- Add all WikiLinks from the analysis
- Save to the correct subdirectory by page_type

Raw source text is saved to `wiki/raw/sources/` unchanged. LLMs read it; never modify it.

---

## Three Operations

```
wiki.ingest(text, topic_hint)   → two-step capture → wiki page
wiki.query(question)            → index → relevant pages → synthesised answer
wiki.lint()                     → health check → LintReport
```

---

## Log & Index

- `wiki/log.md` — append-only chronological record. Never delete entries.
- `wiki/index.md` — content catalog. Updated after every ingest.
- `wiki/overview.md` — auto-regenerated global summary. Human may edit.

---

## Karpathy's Three Layers (Architecture)

```
Layer 1: wiki/raw/sources/    ← Human writes, LLM reads only (immutable)
Layer 2: wiki/                ← LLM writes, human can edit (the wiki proper)
Layer 3: CLAUDE.md            ← Human + LLM co-evolve (this file)
```

The key insight: sources are immutable. The LLM's job is to build a structured
knowledge graph ON TOP of sources, not to paraphrase them verbatim.

---

## Quality Rules

1. **No hallucination** — every factual claim must trace to a source page
2. **No orphans** — every page must appear in `index.md` and have at least one inbound link
3. **Contradiction tracking** — when two sources conflict, create a `synthesis` page noting the conflict
4. **Confidence decay** — older pages with no confirming sources should drop confidence over time
5. **Lint regularly** — run `wiki.lint()` after every 5 ingests

---

## BMAD Integration

When the workflow produces outputs, the final approved output is ingested into the wiki
as a `synthesis` page tagged with the project name. This builds institutional memory
across workflow runs.

---

## Purpose File

`purpose.md` is the wiki's soul — it defines:
- What questions we're trying to answer
- What domain we're researching
- What the evolving thesis is
- What sources are in scope

Update `purpose.md` as understanding grows. The LLM reads it on every operation.
