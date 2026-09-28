"""
agents/miras.py — Miras Framework (The Orchestrator)
Based on: github.com/ofFBeaT9/miras

Responsibility: Sub-agent routing and sequential state/memory handoffs.
Each BMAD Story is routed to a role-matched sub-agent. Declared dependency
deliverables are passed in a bounded context; all outputs remain in AgentState.

New in v1.1:
  run_parallel() — executes independent stories concurrently via
    ThreadPoolExecutor using Kahn's topological-batch algorithm.
  Adaptive temperature — low/medium/high story complexity maps to
    0.1 / 0.2 / 0.35 so deterministic stories stay deterministic.
"""

from __future__ import annotations

import concurrent.futures
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from agents.bmad import Blueprint, BMADAgent, Story
from agents.context import pack_sections

AGENT_SYSTEM_TEMPLATE = """You are a specialised sub-agent in the m1frame multi-agent system.
Your assigned role: {role}

System context:
{context}

Prior agent deliverables (bounded context; omissions marked):
{state_summary}

Focus ONLY on your assigned story. Be precise and complete.
Return the deliverable with a concise explanation of decisions and any limitations.
Do not claim code was executed or tests passed without execution evidence.
"""

# Adaptive temperature — maps story complexity to temperature
_COMPLEXITY_TEMP: dict[str, float] = {
    "low":    0.1,   # deterministic: planning, research, analysis
    "medium": 0.2,   # default
    "high":   0.35,  # creative: architecture design, synthesis
}


@dataclass
class AgentState:
    """Mutable state passed sequentially between sub-agents (Miras pattern)."""
    goal: str
    blueprint_summary: str
    outputs: dict[int, str] = field(default_factory=dict)   # story_id → result
    metadata: dict[str, Any] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def summary(self, max_chars: int = 16000, story_ids: list[int] | None = None) -> str:
        with self._lock:
            ids = sorted(self.outputs) if story_ids is None else list(dict.fromkeys(story_ids))
            sections = [(f"Story {sid}", self.outputs[sid]) for sid in ids if sid in self.outputs]
        return pack_sections(sections, max_chars) if sections else "No prior outputs yet."

    def add_result(self, story_id: int, result: str) -> None:
        with self._lock:
            self.outputs[story_id] = result

    def final_output(self) -> str:
        """Concatenate all story outputs into a single deliverable document."""
        with self._lock:
            parts = [
                f"## Story {sid}\n{result}"
                for sid, result in sorted(self.outputs.items())
            ]
        return "\n\n---\n\n".join(parts)

    def get_result(self, story_id: int) -> str | None:
        with self._lock:
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
    "other":     "General Assistant — complete the task with care and precision.",
    # OpenPlanter (Pillar 3)
    "investigator": "OpenPlanter Investigator — ingest datasets, resolve entities, cross-reference sources, surface non-obvious connections.",
}


class MirasOrchestrator:
    """
    Routes a Blueprint's stories to role-matched sub-agents.

    Two execution modes:
      run()          — sequential (default); guaranteed order, safest for
                       stories with tightly-coupled outputs.
      run_parallel() — concurrent; independent stories (no shared deps) execute
                       in a thread pool, halving wall-clock time on wide backlogs.

    Usage:
        orchestrator = MirasOrchestrator(llm_client)
        state = orchestrator.run(blueprint)               # sequential
        state = orchestrator.run_parallel(blueprint)      # parallel
        print(state.final_output())
    """

    def __init__(
        self,
        llm_client,
        config: dict | None = None,
        on_subtask_start: Callable[[Story], None] | None = None,
        on_subtask_done: Callable[[Story, str], None] | None = None,
        scientific_library=None,
        scientific_config: dict | None = None,
    ):
        self.llm = llm_client
        self.cfg = config or {}
        self.max_agents = self.cfg.get("max_agents", 5)
        self.on_subtask_start = on_subtask_start
        self.on_subtask_done = on_subtask_done
        self.scientific_library = scientific_library
        self.scientific_config = scientific_config or {}

    # ── Sequential execution (original behaviour) ─────────────────────────────

    def run(self, blueprint: Blueprint, purpose_context: str = "") -> AgentState:
        """Execute all stories in dependency order, returning the final AgentState."""
        issues = BMADAgent(self.llm).validate(blueprint, allowed_roles=set(ROLE_MAP))
        if issues:
            raise ValueError("Invalid blueprint: " + "; ".join(issues))
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
                raise RuntimeError(f"Story {story_id} failed; dependent work stopped") from exc

        return state

    # ── Parallel execution (Kahn's topological-batch algorithm) ──────────────

    def run_parallel(
        self,
        blueprint: Blueprint,
        purpose_context: str = "",
        max_workers: int | None = None,
    ) -> AgentState:
        """
        Execute independent stories concurrently using a thread pool.

        Algorithm: Kahn's topological sort, executed in batches.
        Each batch contains all stories whose dependencies are already complete.
        Stories within a batch run in parallel; batches execute sequentially.

        This is safe because each batch only starts after the previous batch
        has fully settled, so AgentState always reflects complete prior work.
        """
        issues = BMADAgent(self.llm).validate(blueprint, allowed_roles=set(ROLE_MAP))
        if issues:
            raise ValueError("Invalid blueprint: " + "; ".join(issues))
        state = AgentState(
            goal=blueprint.goal_summary,
            blueprint_summary=blueprint.summary(),
        )
        story_map = {s.id: s for s in blueprint.stories}
        in_degree: dict[int, int] = {s.id: len(s.depends_on) for s in blueprint.stories}
        dependents: dict[int, list[int]] = {s.id: [] for s in blueprint.stories}
        for s in blueprint.stories:
            for dep in s.depends_on:
                dependents.setdefault(dep, []).append(s.id)

        workers = max_workers or min(self.max_agents, 8)
        ready = [sid for sid, deg in in_degree.items() if deg == 0]

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while ready:
                futures = {}
                for sid in ready:
                    story = story_map[sid]
                    if self.on_subtask_start:
                        self.on_subtask_start(story)
                    story.status = "running"
                    fut = pool.submit(self._execute_story, story, state, purpose_context)
                    futures[fut] = story

                next_ready: list[int] = []
                for fut, story in futures.items():
                    try:
                        result = fut.result()
                        state.add_result(story.id, result)
                        story.result = result
                        story.status = "done"
                        if self.on_subtask_done:
                            self.on_subtask_done(story, result)
                    except Exception as exc:
                        state.add_result(story.id, f"[ERROR] {exc}")
                        story.status = "failed"
                        raise RuntimeError(f"Story {story.id} failed; dependent work stopped") from exc

                    for dep_id in dependents.get(story.id, []):
                        in_degree[dep_id] -= 1
                        if in_degree[dep_id] == 0:
                            next_ready.append(dep_id)

                ready = next_ready

        return state

    # ── Single-task helper ────────────────────────────────────────────────────

    def route_single(self, task: str, role: str = "other", context: str = "") -> str:
        """Execute a single task without a Blueprint — useful for quick one-off calls."""
        context = self._scientific_context(task, context)
        system = AGENT_SYSTEM_TEMPLATE.format(
            role=ROLE_MAP.get(role, ROLE_MAP["other"]),
            context=context or "No additional context.",
            state_summary="No prior outputs.",
        )
        return self.llm.chat(prompt=task, system=system, temperature=0.2)

    # ── Private ───────────────────────────────────────────────────────────────

    def _scientific_context(self, task: str, context: str) -> str:
        if self.scientific_library is None:
            return context
        reference, _ = self.scientific_library.context(
            task, names=self.scientific_config.get("skills"),
            max_chars=int(self.scientific_config.get("max_context_chars", 60000)))
        return "\n\n".join(filter(None, [context, reference]))

    def _execute_story(self, story: Story, state: AgentState, context: str) -> str:
        context = self._scientific_context(
            f"{state.goal} {story.title} {story.description}", context)
        role_key = story.role or story.type or "other"
        role_desc = ROLE_MAP.get(role_key, ROLE_MAP["other"])

        system = AGENT_SYSTEM_TEMPLATE.format(
            role=role_desc,
            context=context or "No additional context.",
            state_summary=state.summary(
                max_chars=int(self.cfg.get("context_max_chars", 16000)),
                story_ids=story.depends_on,
            ),
        )

        # Adaptive temperature: complex stories get slightly higher temperature
        # for richer output; low-complexity stays fully deterministic.
        temperature = _COMPLEXITY_TEMP.get(story.complexity, 0.2)

        ac_lines = "\n".join(f"  - {c}" for c in story.acceptance_criteria) if story.acceptance_criteria else ""
        ac_section = f"\n\nAcceptance Criteria:\n{ac_lines}" if ac_lines else ""

        prompt = (
            f"Overall goal: {state.goal}\n\n"
            f"Story #{story.id} [{role_key.upper()}]: {story.title}\n\n"
            f"Description: {story.description}{ac_section}\n\n"
            f"Complexity: {story.complexity}"
        )
        return self.llm.chat(prompt=prompt, system=system, temperature=temperature)
