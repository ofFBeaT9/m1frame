"""
agents/openplanter.py — OpenPlanter Integration (Pillar 3: Investigation Layer)
Based on: github.com/ShinMegamiBoson/OpenPlanter

OpenPlanter is a recursive investigation agent that ingests heterogeneous datasets
(corporate registries, campaign finance, lobbying disclosures, government contracts),
resolves entities across them, and surfaces non-obvious connections through
evidence-backed analysis.

In m1frame it operates as Pillar 3 — invoked automatically when BMAD assigns
a story the role "investigator", or called directly via OpenPlanterAgent.investigate().

New in v1.1:
  Voyage embeddings — when VOYAGE_API_KEY is set, resolve_entities() uses
    semantic similarity instead of exact string matching.
  Exa web search — when EXA_API_KEY is set, investigate() fetches live web
    search results to enrich dataset investigations.

Tools available (from OpenPlanter's 19-tool suite, abstracted here):
  Dataset tools  — list_files, search_files, read_file, write_file, repo_map
  Shell tools    — run_shell (analysis scripts, data pipelines)
  Web tools      — web_search (via EXA_API_KEY), fetch_url, recursive sub-agents
  Analysis tools — entity_resolution, cross_reference, surface_connections

Supported backends (OpenPlanter providers):
  anthropic  → claude-opus-4-7  (ANTHROPIC_API_KEY)
  openai     → gpt-4o           (OPENAI_API_KEY)
  openrouter → claude-sonnet    (OPENROUTER_API_KEY)
  cerebras   → qwen-3-235b      (CEREBRAS_API_KEY)
"""

from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Prompts ───────────────────────────────────────────────────────────────────

INVESTIGATION_SYSTEM = """You are an OpenPlanter Investigation Agent.
Your specialty: ingesting heterogeneous datasets and surfacing non-obvious connections
through evidence-backed, recursive analysis.

You have access to these conceptual tool categories:
  1. Dataset ingestion  — read files, map repos, search within datasets
  2. Shell execution    — run analysis scripts and data pipelines
  3. Web research       — search the web, fetch URLs, resolve entities online
  4. Sub-agent delegation — spawn recursive investigation threads for sub-tasks
  5. Cross-referencing  — find overlaps between datasets (e.g. vendor payments vs lobbying)

Always begin with a <thought> block:
  - What datasets are relevant?
  - What entities need resolving?
  - What connections are non-obvious?
  - What evidence do I need to surface?

After </thought>, provide:
  1. Investigation Summary
  2. Entity Map (who/what is involved)
  3. Key Connections Found
  4. Evidence Chain
  5. Recommended Follow-up
"""

ENTITY_RESOLUTION_SYSTEM = """You are an Entity Resolution Agent (OpenPlanter sub-agent).
Given raw data from multiple sources, resolve all references to the same real-world entity.

Rules:
- Treat name variants, abbreviations, and aliases as the same entity
- Flag low-confidence matches explicitly
- Output a canonical entity list with all known aliases

Respond in JSON:
{
  "entities": [
    {
      "canonical_name": "...",
      "aliases": ["...", "..."],
      "entity_type": "person|org|contract|transaction|location",
      "confidence": "high|medium|low",
      "sources": ["..."]
    }
  ],
  "unresolved": ["..."],
  "conflicts": ["..."]
}
No preamble. Pure JSON only.
"""

CROSS_REFERENCE_SYSTEM = """You are a Cross-Reference Agent (OpenPlanter sub-agent).
Given two or more entity lists or datasets, find overlaps, conflicts, and non-obvious connections.

Look for:
- Same entity appearing in multiple datasets under different roles
- Financial flows between connected entities
- Temporal correlations (events happening close together)
- Structural patterns (same addresses, phone numbers, directors)

Respond in JSON:
{
  "direct_matches": [{"entity": "...", "datasets": ["..."], "significance": "..."}],
  "indirect_connections": [{"path": ["entity_a", "via", "entity_b"], "significance": "..."}],
  "flags": [{"type": "conflict|anomaly|pattern", "description": "...", "severity": "high|medium|low"}],
  "summary": "..."
}
No preamble. Pure JSON only.
"""

SEMANTIC_ENTITY_SYSTEM = """You are a Semantic Entity Matching Agent.
Given a list of entity candidates with similarity scores, merge those that refer to
the same real-world entity, even if their names differ significantly.

Use contextual clues: industry, location, date ranges, associated people.

Respond in JSON:
{
  "merged_entities": [
    {
      "canonical_name": "...",
      "members": ["...", "..."],
      "merge_confidence": "high|medium|low",
      "rationale": "..."
    }
  ]
}
No preamble. Pure JSON only.
"""


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Entity:
    canonical_name: str
    aliases: list[str]
    entity_type: str          # person | org | contract | transaction | location
    confidence: str           # high | medium | low
    sources: list[str]


@dataclass
class Connection:
    path: list[str]           # ["entity_a", "via", "entity_b"]
    significance: str


@dataclass
class InvestigationFlag:
    flag_type: str            # conflict | anomaly | pattern
    description: str
    severity: str             # high | medium | low


@dataclass
class InvestigationResult:
    """Full result from an OpenPlanter investigation run."""
    task: str
    summary: str
    entities: list[Entity] = field(default_factory=list)
    direct_matches: list[dict] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list)
    flags: list[InvestigationFlag] = field(default_factory=list)
    thought_chain: str = ""
    raw_analysis: str = ""
    workspace_files: list[str] = field(default_factory=list)
    web_results: list[dict] = field(default_factory=list)

    def report(self) -> str:
        lines = [
            f"Investigation: {self.task}",
            f"Summary: {self.summary}",
        ]
        if self.entities:
            lines.append(f"Entities resolved: {len(self.entities)}")
            for e in self.entities[:5]:
                lines.append(f"  • {e.canonical_name} [{e.entity_type}] ({e.confidence})")
        if self.flags:
            lines.append("Flags:")
            for f in self.flags:
                lines.append(f"  [{f.severity.upper()}] {f.description}")
        if self.connections:
            lines.append("Key connections:")
            for c in self.connections[:3]:
                lines.append(f"  → {' → '.join(c.path)}: {c.significance}")
        if self.web_results:
            lines.append(f"Web sources consulted: {len(self.web_results)}")
        return "\n".join(lines)


# ── Main class ────────────────────────────────────────────────────────────────

class OpenPlanterAgent:
    """
    OpenPlanter Investigation Agent — Pillar 3 of m1frame.

    Wraps OpenPlanter's recursive investigation pattern, providing:
      - investigate(task, datasets)  → full InvestigationResult
      - resolve_entities(raw_data)   → canonical entity list (Voyage-powered when available)
      - cross_reference(datasets)    → overlaps and connections

    Exa web search: set EXA_API_KEY to enrich investigations with live web data.
    Voyage embeddings: set VOYAGE_API_KEY for semantic entity matching.

    # BETA: workspace file I/O and shell execution require OpenPlanter installed:
    #   pip install git+https://github.com/ShinMegamiBoson/OpenPlanter.git
    # Without it, the agent operates in LLM-only mode (all reasoning, no real file/shell tools).
    """

    SUPPORTED_PROVIDERS = {
        "anthropic":  {"model": "claude-opus-4-7",               "key_env": "ANTHROPIC_API_KEY"},
        "openai":     {"model": "gpt-4o",                        "key_env": "OPENAI_API_KEY"},
        "openrouter": {"model": "anthropic/claude-sonnet-4-5",   "key_env": "OPENROUTER_API_KEY"},
        "cerebras":   {"model": "qwen-3-235b-a22b-instruct-2507","key_env": "CEREBRAS_API_KEY"},
    }

    def __init__(
        self,
        llm_client,
        config: Optional[dict] = None,
        workspace: Optional[str] = None,
    ) -> None:
        self.llm = llm_client
        self.cfg = config or {}
        self.workspace = Path(workspace) if workspace else Path("workspace")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._openplanter_available = self._check_openplanter()
        self._exa_key = os.environ.get("EXA_API_KEY", "")
        self._voyage_key = os.environ.get("VOYAGE_API_KEY", "")

    # ── Public API ────────────────────────────────────────────────────────────

    def investigate(self, task: str, datasets: Optional[list[str]] = None) -> InvestigationResult:
        """
        Run a full OpenPlanter investigation on a task.

        When EXA_API_KEY is set, performs real web searches to enrich the
        investigation context before the LLM analysis pass.

        Args:
            task:     Natural language investigation task.
            datasets: Optional list of file paths or URLs to include as context.

        Returns:
            InvestigationResult with entities, connections, flags, and summary.
        """
        dataset_context = ""
        if datasets:
            dataset_context = "\n\nDatasets provided:\n" + "\n".join(f"  - {d}" for d in datasets)

        # Optionally enrich with Exa web search results
        web_results: list[dict] = []
        web_context = ""
        if self._exa_key:
            web_results = self._exa_search(task)
            if web_results:
                web_context = "\n\nWeb search results:\n" + "\n".join(
                    f"  [{r.get('title','')}] {r.get('url','')}: {r.get('text','')[:200]}"
                    for r in web_results[:5]
                )

        raw = self.llm.chat(
            prompt=f"Investigation task: {task}{dataset_context}{web_context}",
            system=INVESTIGATION_SYSTEM,
            temperature=0.2,
        )

        # Parse thought chain
        thought = ""
        answer = raw
        m = re.search(r"<thought>(.*?)</thought>", raw, re.DOTALL)
        if m:
            thought = m.group(1).strip()
            answer = raw[m.end():].strip()

        # Save raw output to workspace
        out_file = self.workspace / "investigation_result.md"
        out_file.write_text(f"# Investigation: {task}\n\n{answer}", encoding="utf-8")

        return InvestigationResult(
            task=task,
            summary=answer[:500],
            thought_chain=thought,
            raw_analysis=answer,
            workspace_files=[str(out_file)],
            web_results=web_results,
        )

    def resolve_entities(self, raw_data: str) -> list[Entity]:
        """
        Resolve entity references across raw dataset text.

        When VOYAGE_API_KEY is set, performs Voyage embedding-based semantic
        matching as a post-processing step to merge near-duplicate entities
        that an LLM might miss due to name variation.

        Returns a canonical entity list with aliases and confidence scores.
        """
        raw = self.llm.chat(
            prompt=f"Resolve entities in this data:\n\n{raw_data[:4000]}",
            system=ENTITY_RESOLUTION_SYSTEM,
            temperature=0.1,
        )
        try:
            data = _parse_json(raw)
            entities = [
                Entity(
                    canonical_name=e.get("canonical_name", "Unknown"),
                    aliases=e.get("aliases", []),
                    entity_type=e.get("entity_type", "org"),
                    confidence=e.get("confidence", "medium"),
                    sources=e.get("sources", []),
                )
                for e in data.get("entities", [])
            ]
        except ValueError:
            return []

        # Voyage semantic merge (optional)
        if self._voyage_key and len(entities) > 1:
            entities = self._voyage_merge_entities(entities)

        return entities

    def cross_reference(self, dataset_a: str, dataset_b: str) -> InvestigationResult:
        """
        Cross-reference two datasets to find overlaps, conflicts, and patterns.
        Maps to OpenPlanter's core use case: vendor payments vs lobbying disclosures, etc.
        """
        prompt = (
            f"Cross-reference these two datasets and find overlaps, patterns, and anomalies.\n\n"
            f"Dataset A:\n{dataset_a[:2000]}\n\n"
            f"Dataset B:\n{dataset_b[:2000]}"
        )
        raw = self.llm.chat(prompt=prompt, system=CROSS_REFERENCE_SYSTEM, temperature=0.1)
        try:
            data = _parse_json(raw)
            connections = [
                Connection(path=c.get("path", []), significance=c.get("significance", ""))
                for c in data.get("indirect_connections", [])
            ]
            flags = [
                InvestigationFlag(
                    flag_type=f.get("type", "anomaly"),
                    description=f.get("description", ""),
                    severity=f.get("severity", "medium"),
                )
                for f in data.get("flags", [])
            ]
            return InvestigationResult(
                task="cross_reference",
                summary=data.get("summary", ""),
                direct_matches=data.get("direct_matches", []),
                connections=connections,
                flags=flags,
                raw_analysis=raw,
            )
        except ValueError:
            return InvestigationResult(task="cross_reference", summary=raw[:300])

    def miras_handler(self, task: str, state_context: str = "") -> str:
        """
        Called by MirasOrchestrator when a story has role='investigator'.
        Returns a plain string result suitable for AgentState.
        """
        result = self.investigate(task)
        return result.report()

    # ── Exa web search ────────────────────────────────────────────────────────

    def _exa_search(self, query: str, num_results: int = 5) -> list[dict]:
        """Fetch live web results via Exa API. Returns [] if unavailable."""
        try:
            from exa_py import Exa
            exa = Exa(self._exa_key)
            response = exa.search_and_contents(
                query,
                num_results=num_results,
                text={"max_characters": 300},
            )
            return [
                {
                    "title": r.title or "",
                    "url": r.url or "",
                    "text": getattr(r, "text", "") or "",
                }
                for r in response.results
            ]
        except Exception:
            return []

    # ── Voyage semantic entity merging ────────────────────────────────────────

    def _voyage_merge_entities(self, entities: list[Entity]) -> list[Entity]:
        """
        Use Voyage embeddings to find semantically similar entity names and
        merge them via a secondary LLM call (SEMANTIC_ENTITY_SYSTEM).
        Falls back to returning entities unchanged if Voyage is unavailable.
        """
        try:
            import voyageai
            vo = voyageai.Client(api_key=self._voyage_key)
            names = [e.canonical_name for e in entities]
            result = vo.embed(names, model="voyage-3", input_type="document")
            vectors = result.embeddings

            # Build similarity pairs (cosine similarity > 0.92 = likely same entity)
            import math
            candidates: list[dict] = []
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    sim = _cosine(vectors[i], vectors[j])
                    if sim > 0.92:
                        candidates.append({
                            "a": names[i],
                            "b": names[j],
                            "similarity": round(sim, 3),
                        })

            if not candidates:
                return entities

            # Ask LLM to confirm merges
            raw = self.llm.chat(
                prompt=f"Candidate entity merges (similarity > 0.92):\n{json.dumps(candidates, indent=2)}\n\nOriginal entities:\n{json.dumps(names)}",
                system=SEMANTIC_ENTITY_SYSTEM,
                temperature=0.1,
            )
            data = _parse_json(raw)
            merged_map: dict[str, str] = {}  # member → canonical
            for merge in data.get("merged_entities", []):
                canon = merge.get("canonical_name", "")
                if merge.get("merge_confidence") in ("high", "medium"):
                    for member in merge.get("members", []):
                        merged_map[member] = canon

            # Apply merges
            updated: list[Entity] = []
            seen_canonical: set[str] = set()
            for e in entities:
                canon = merged_map.get(e.canonical_name, e.canonical_name)
                if canon not in seen_canonical:
                    seen_canonical.add(canon)
                    updated.append(Entity(
                        canonical_name=canon,
                        aliases=list({e.canonical_name, *e.aliases}),
                        entity_type=e.entity_type,
                        confidence=e.confidence,
                        sources=e.sources,
                    ))
            return updated or entities

        except Exception:
            return entities

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _check_openplanter() -> bool:
        """Check whether the real OpenPlanter package is installed."""
        try:
            import importlib
            importlib.import_module("openplanter")
            return True
        except ImportError:
            return False

    @property
    def mode(self) -> str:
        parts = ["full" if self._openplanter_available else "llm-only"]
        if self._exa_key:
            parts.append("exa")
        if self._voyage_key:
            parts.append("voyage")
        return "+".join(parts)

    def __repr__(self) -> str:
        return f"<OpenPlanterAgent mode={self.mode} workspace={self.workspace}>"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    clean = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse failed: {exc}") from exc


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
