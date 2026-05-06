"""
agents/openplanter.py — OpenPlanter Integration (Pillar 7: Investigation Layer)
Based on: github.com/ShinMegamiBoson/OpenPlanter

OpenPlanter is a recursive investigation agent that ingests heterogeneous datasets
(corporate registries, campaign finance, lobbying disclosures, government contracts),
resolves entities across them, and surfaces non-obvious connections through
evidence-backed analysis.

In m1frame it operates as Pillar 7 — invoked automatically when BMAD assigns
a story the role "investigator", or called directly via OpenPlanterAgent.investigate().

Tools available (from OpenPlanter's 19-tool suite, abstracted here):
  Dataset tools  — list_files, search_files, read_file, write_file, repo_map
  Shell tools    — run_shell (analysis scripts, data pipelines)
  Web tools      — web_search (via EXA_API_KEY), fetch_url, recursive sub-agents
  Analysis tools — entity_resolution, cross_reference, surface_connections

Supported backends (OpenPlanter providers):
  anthropic  → claude-opus-4-6  (ANTHROPIC_API_KEY)
  openai     → gpt-4o           (OPENAI_API_KEY)
  openrouter → claude-sonnet    (OPENROUTER_API_KEY)
  cerebras   → qwen-3-235b      (CEREBRAS_API_KEY)
"""

from __future__ import annotations
import json
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
        return "\n".join(lines)


# ── Main class ────────────────────────────────────────────────────────────────

class OpenPlanterAgent:
    """
    OpenPlanter Investigation Agent — Pillar 7 of m1frame.

    Wraps OpenPlanter's recursive investigation pattern, providing:
      - investigate(task, datasets)  → full InvestigationResult
      - resolve_entities(raw_data)   → canonical entity list
      - cross_reference(datasets)    → overlaps and connections

    Used automatically by Miras when a BMAD story has role="investigator".
    Can also be called directly for standalone dataset investigations.

    # BETA: workspace file I/O and shell execution require OpenPlanter installed:
    #   pip install git+https://github.com/ShinMegamiBoson/OpenPlanter.git
    # Without it, the agent operates in LLM-only mode (no real file/shell tools).
    """

    SUPPORTED_PROVIDERS = {
        "anthropic":  {"model": "claude-opus-4-6",               "key_env": "ANTHROPIC_API_KEY"},
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

    # ── Public API ────────────────────────────────────────────────────────────

    def investigate(self, task: str, datasets: Optional[list[str]] = None) -> InvestigationResult:
        """
        Run a full OpenPlanter investigation on a task.

        Args:
            task:     Natural language investigation task.
                      e.g. "Cross-reference vendor payments against lobbying disclosures"
            datasets: Optional list of file paths or URLs to include as context.

        Returns:
            InvestigationResult with entities, connections, flags, and summary.
        """
        dataset_context = ""
        if datasets:
            dataset_context = "\n\nDatasets provided:\n" + "\n".join(f"  - {d}" for d in datasets)

        raw = self.llm.chat(
            prompt=f"Investigation task: {task}{dataset_context}",
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
        out_file.write_text(f"# Investigation: {task}\n\n{answer}")

        return InvestigationResult(
            task=task,
            summary=answer[:500],
            thought_chain=thought,
            raw_analysis=answer,
            workspace_files=[str(out_file)],
        )

    def resolve_entities(self, raw_data: str) -> list[Entity]:
        """
        Resolve entity references across raw dataset text.
        Returns a canonical entity list with aliases and confidence scores.
        """
        raw = self.llm.chat(
            prompt=f"Resolve entities in this data:\n\n{raw_data[:4000]}",
            system=ENTITY_RESOLUTION_SYSTEM,
            temperature=0.1,
        )
        try:
            data = _parse_json(raw)
            return [
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
        return "full" if self._openplanter_available else "llm-only"

    def __repr__(self) -> str:
        return f"<OpenPlanterAgent mode={self.mode} workspace={self.workspace}>"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    clean = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse failed: {exc}") from exc
