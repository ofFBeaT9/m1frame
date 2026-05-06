"""
agents/miras.py — Miras Framework (The Orchestrator)
Based on: github.com/ofFBeaT9/miras

Responsibility: Sub-agent routing and sequential state/memory handoffs.
Each BMAD Story is routed to a role-matched sub-agent. The full AgentState
is passed between agents so every agent has access to all prior work.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from agents.bmad import Blueprint, Story


AGENT_SYSTEM_TEMPLATE = """You are a specialised sub-agent in the m1frame multi-agent system.
Your assigned role: {role}

System context:
{context}

Prior agent outputs (full state so far):
{state_summary}

Focus ONLY on your assigned story. Be precise and complete.
Always begin your response with a <thought> block where you reason step-by-step before answering.
After </thought> give your full deliverable for this story.
"""


@dataclass
class AgentState:
    """Mutable state passed sequentially between sub-agents (Miras pattern)."""
    goal: str
    blueprint_summary: str
    outputs: dict[int, str] = field(default_factory=dict)   # story_id → result
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self, max_chars: int = 3000) -> str:
        if not self.outputs:
            return "No prior outputs yet."
        lines = []
        for sid, result in self.outputs.items():
            snippet = result[:500] + "..." if len(result) > 500 else result
            lines.append(f"[Story {sid}]:\n{snippet}")
        return "\n\n".join(lines)[:max_chars]

    def add_result(self, story_id: int, result: str) -> None:
        self.outputs[story_id] = result

    def final_output(self) -> str:
        """Concatenate all story outputs into a single deliverable document."""
        parts = [
            f"## Story {sid}\n{result}"
            for sid, result in sorted(self.outputs.items())
        ]
        return "\n\n---\n\n".join(parts)

    def get_result(self, story_id: int) -> Optional[str]:
        return self.outputs.get(story_id)


# Role descriptions aligned with BMAD roles + generic fallbacks
ROLE_MAP: dict[str, str] = {
    # BMAD agile roles (bmad-code-org/BMAD-METHOD)
    "analyst":      "Business Analyst — elicit requirements, produce a PRD with user stories and acceptance criteria.",
    "architect":    "Software Architect — design the system, make tech decisions, produce architecture docs.",
    "dev":          "Senior Developer — implement stories cleanly with tested, production-ready code.",
    "qa":           "QA Engineer — write test plans, identify edge cases, validate all acceptance criteria.",
    "scrum_master": "Scrum Master — decompose work, manage dependencies, keep scope tight and delivery moving.",
    "pm":           "Product Manager — prioritise the backlog, define MVP scope, roadmap, and success metrics.",
    # Generic fallbacks
    "research":  "Research Analyst — gather, summarise, and cite relevant information.",
    "code":      "Senior Software Engineer — write clean, tested, well-documented code.",
    "analysis":  "Data & Logic Analyst — reason rigorously and draw evidence-based conclusions.",
    "writing":   "Technical Writer — produce clear, structured, professional prose.",
    "other":        "General Assistant — complete the task with care and precision.",
    # OpenPlanter (Pillar 7)
    "investigator": "OpenPlanter Investigator — ingest datasets, resolve entities, cross-reference sources, surface non-obvious connections.",
}


class MirasOrchestrator:
    """
    Routes a Blueprint's stories to role-matched sub-agents in dependency order,
    passing a shared AgentState through every sequential handoff.

    Usage:
        orchestrator = MirasOrchestrator(llm_client)
        state = orchestrator.run(blueprint)
        print(state.final_output())
    """

    def __init__(
        self,
        llm_client,
        config: Optional[dict] = None,
        on_subtask_start: Optional[Callable[[Story], None]] = None,
        on_subtask_done: Optional[Callable[[Story, str], None]] = None,
    ):
        self.llm = llm_client
        self.cfg = config or {}
        self.max_agents = self.cfg.get("max_agents", 5)
        self.on_subtask_start = on_subtask_start
        self.on_subtask_done = on_subtask_done

    def run(self, blueprint: Blueprint, purpose_context: str = "") -> AgentState:
        """Execute all stories in dependency order, returning the final AgentState."""
        state = AgentState(
            goal=blueprint.goal_summary,
            blueprint_summary=blueprint.summary(),
        )
        executed: set[int] = set()

        for story_id in blueprint.execution_order:
            story = blueprint.get_subtask(story_id)
            if story is None:
                continue

            missing_deps = [d for d in story.depends_on if d not in executed]
            if missing_deps:
                raise RuntimeError(
                    f"Story {story_id} depends on {missing_deps} which haven't run yet. "
                    f"Check execution_order in the Blueprint."
                )

            if self.on_subtask_start:
                self.on_subtask_start(story)

            story.status = "running"
            try:
                result = self._execute_story(story, state, purpose_context)
                state.add_result(story_id, result)
                story.result = result
                story.status = "done"
                executed.add(story_id)
                if self.on_subtask_done:
                    self.on_subtask_done(story, result)
            except Exception as exc:
                story.status = "failed"
                state.add_result(story_id, f"[ERROR] {exc}")
                executed.add(story_id)

        return state

    def route_single(self, task: str, role: str = "other", context: str = "") -> str:
        """Execute a single task without a Blueprint — useful for quick one-off calls."""
        system = AGENT_SYSTEM_TEMPLATE.format(
            role=ROLE_MAP.get(role, ROLE_MAP["other"]),
            context=context or "No additional context.",
            state_summary="No prior outputs.",
        )
        return self.llm.chat(prompt=task, system=system, temperature=0.2)

    def _execute_story(self, story: Story, state: AgentState, context: str) -> str:
        role_key = story.role or story.type or "other"
        role_desc = ROLE_MAP.get(role_key, ROLE_MAP["other"])

        system = AGENT_SYSTEM_TEMPLATE.format(
            role=role_desc,
            context=context or "No additional context.",
            state_summary=state.summary(),
        )

        ac_lines = "\n".join(f"  - {c}" for c in story.acceptance_criteria) if story.acceptance_criteria else ""
        ac_section = f"\n\nAcceptance Criteria:\n{ac_lines}" if ac_lines else ""

        prompt = (
            f"Story #{story.id} [{role_key.upper()}]: {story.title}\n\n"
            f"Description: {story.description}{ac_section}\n\n"
            f"Complexity: {story.complexity}"
        )
        return self.llm.chat(prompt=prompt, system=system, temperature=0.2)
