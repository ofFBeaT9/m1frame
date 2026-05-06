"""
agents/bmad.py — BMAD Method (The Blueprint)
Based on: github.com/bmad-code-org/BMAD-METHOD (42k stars)

BMAD = Breakthrough Method for Agile AI-Driven Development.
Uses specialized AI agents, each playing a distinct agile role:
  - Analyst (BA)     : Elicit requirements, produce PRD
  - Architect        : System design, tech decisions, architecture doc
  - Developer (Dev)  : Implement stories, write code
  - QA Engineer      : Test plans, validation, bug reports
  - Scrum Master (SM): Sprint planning, story decomposition, dependency tracking
  - Product Manager  : Prioritisation, roadmap, acceptance criteria

The Blueprint phase produces an ordered story list and architecture brief
that Miras agents then execute sequentially.
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional


# ── BMAD Role Definitions (from the actual BMAD-METHOD repo) ─────────────────

BMAD_ROLES = {
    "analyst": {
        "title": "Business Analyst",
        "mandate": "Elicit and document requirements. Produce a concise PRD with user stories and acceptance criteria.",
    },
    "architect": {
        "title": "Software Architect",
        "mandate": "Design the system. Produce architecture decisions, tech stack, component breakdown, and data flow.",
    },
    "dev": {
        "title": "Senior Developer",
        "mandate": "Implement stories cleanly. Write tested, production-ready code with clear comments.",
    },
    "qa": {
        "title": "QA Engineer",
        "mandate": "Validate outputs. Write test plans, identify edge cases, and confirm acceptance criteria are met.",
    },
    "scrum_master": {
        "title": "Scrum Master",
        "mandate": "Decompose work into atomic stories. Manage dependencies. Keep scope tight and delivery moving.",
    },
    "pm": {
        "title": "Product Manager",
        "mandate": "Prioritise the backlog. Define MVP scope, roadmap, and success metrics.",
    },
}

BMAD_SYSTEM = """You are a BMAD Scrum Master Agent.
Your job: decompose a product goal into an ordered, dependency-aware story backlog.

BMAD Role Assignments per story:
  research/analysis → analyst
  architecture      → architect
  coding/feature    → dev
  testing/qa        → qa
  planning          → scrum_master

Output ONLY valid JSON matching this schema (no markdown fences):
{
  "project_name": "...",
  "goal_summary": "...",
  "domain": "...",
  "mvp_scope": "...",
  "constraints": ["..."],
  "stories": [
    {
      "id": 1,
      "title": "...",
      "role": "analyst|architect|dev|qa|scrum_master|pm",
      "type": "research|architecture|code|test|planning|writing|other",
      "complexity": "low|medium|high",
      "depends_on": [],
      "acceptance_criteria": ["..."],
      "description": "..."
    }
  ],
  "execution_order": [1, 2, 3],
  "architecture_notes": "..."
}
"""


@dataclass
class Story:
    """A BMAD user story — the atomic unit of work."""
    id: int
    title: str
    role: str           # analyst | architect | dev | qa | scrum_master | pm
    type: str
    complexity: str
    depends_on: list[int]
    acceptance_criteria: list[str]
    description: str
    result: Optional[str] = None
    status: str = "pending"   # pending | running | done | failed

    @property
    def role_info(self) -> dict:
        return BMAD_ROLES.get(self.role, BMAD_ROLES["dev"])


@dataclass
class Blueprint:
    """BMAD project blueprint — the full story backlog with architecture brief."""
    project_name: str
    goal_summary: str
    domain: str
    mvp_scope: str
    constraints: list[str]
    stories: list[Story]
    execution_order: list[int]
    architecture_notes: str
    raw: dict = field(default_factory=dict)

    # Backward compat alias
    @property
    def subtasks(self) -> list[Story]:
        return self.stories

    def get_subtask(self, story_id: int) -> Optional[Story]:
        return next((s for s in self.stories if s.id == story_id), None)

    def get_story(self, story_id: int) -> Optional[Story]:
        return self.get_subtask(story_id)

    def pending_stories(self) -> list[Story]:
        return [s for s in self.stories if s.status == "pending"]

    def summary(self) -> str:
        lines = [
            f"Project: {self.project_name}",
            f"Goal: {self.goal_summary}",
            f"Domain: {self.domain}",
            f"MVP Scope: {self.mvp_scope}",
        ]
        for s in self.stories:
            ac = "; ".join(s.acceptance_criteria[:2])
            lines.append(f"  [{s.id}] [{s.role.upper()}] {s.title} ({s.complexity}) — {s.status}")
            if ac:
                lines.append(f"       AC: {ac}")
        return "\n".join(lines)


class BMADAgent:
    """
    BMAD Scrum Master — decomposes a product goal into an ordered story backlog.
    Assigns each story a BMAD role (analyst, architect, dev, qa, etc.).
    """

    def __init__(self, llm_client, config: Optional[dict] = None):
        self.llm = llm_client
        self.cfg = config or {}
        self.max_subtasks = self.cfg.get("max_subtasks", 10)

    def plan(self, goal: str, extra_context: str = "") -> Blueprint:
        prompt = f"Product goal: {goal}"
        if extra_context:
            prompt += f"\n\nContext:\n{extra_context}"
        prompt += f"\n\nMax stories: {self.max_subtasks}"

        raw_json = self.llm.chat(prompt=prompt, system=BMAD_SYSTEM, temperature=0.1)
        data = self._parse_json(raw_json)
        return self._build_blueprint(data)

    def validate(self, blueprint: Blueprint) -> list[str]:
        """Return a list of validation issues (empty = all good)."""
        issues = []
        ids = {s.id for s in blueprint.stories}
        for s in blueprint.stories:
            for dep in s.depends_on:
                if dep not in ids:
                    issues.append(f"Story {s.id} depends on non-existent story {dep}")
            if s.role not in BMAD_ROLES:
                issues.append(f"Story {s.id} has unknown role '{s.role}'")
        if not blueprint.execution_order:
            issues.append("execution_order is empty")
        if not blueprint.stories:
            issues.append("No stories produced")
        return issues

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = re.sub(r"```(?:json)?", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"BMAD: LLM returned invalid JSON — {e}\nRaw:\n{text}")

    @staticmethod
    def _build_blueprint(data: dict) -> Blueprint:
        stories = [
            Story(
                id=s["id"],
                title=s["title"],
                role=s.get("role", "dev"),
                type=s.get("type", "other"),
                complexity=s.get("complexity", "medium"),
                depends_on=s.get("depends_on", []),
                acceptance_criteria=s.get("acceptance_criteria", []),
                description=s.get("description", ""),
            )
            for s in data.get("stories", [])
        ]
        return Blueprint(
            project_name=data.get("project_name", "Untitled"),
            goal_summary=data.get("goal_summary", ""),
            domain=data.get("domain", "general"),
            mvp_scope=data.get("mvp_scope", ""),
            constraints=data.get("constraints", []),
            stories=stories,
            execution_order=data.get("execution_order", [s.id for s in stories]),
            architecture_notes=data.get("architecture_notes", ""),
            raw=data,
        )
