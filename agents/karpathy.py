"""
agents/karpathy.py — Karpathy Patterns (The Engine)
Responsibility: Concise final-answer synthesis and optional refinement.

New in v1.1:
  self_critique() — two-pass method where the model first produces an answer,
    then critiques it and produces a refined version. Surfaces hidden errors that
    a single-pass generation misses, without needing the full Council.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

KARPATHY_SYSTEM = """You are a precise output synthesizer.
Return only the completed final answer, with a concise explanation or evidence
when useful. Do not expose private reasoning or internal thought blocks.
Do not claim council approval, tool execution or persistence unless supplied
as authoritative runtime evidence. State uncertainty and evidence limits.
Code must be complete and prose factual. No filler.
"""

KARPATHY_REFINEMENT_SYSTEM = """Refine the final answer for correctness and clarity.
Return only the improved final answer, with evidence and limitations.
Do not return private reasoning or process-status claims.
"""

SELF_CRITIQUE_SYSTEM = KARPATHY_REFINEMENT_SYSTEM


@dataclass
class KarpathyResult:
    raw: str
    thought: str
    answer: str
    had_thought_tag: bool

    def __str__(self):
        return self.answer


class KarpathyEngine:
    """
    Wraps LLM calls with Karpathy-style prompting:
    - Final-answer-only prompting
    - Low temperature (not a determinism guarantee)
    - Optional refinement pass
    - self_critique(): two-pass critique → refine loop
    """

    def __init__(self, llm_client, config: dict | None = None):
        self.llm = llm_client
        self.cfg = config or {}
        self.temperature = self.cfg.get("temperature_override", 0.1)
        self.force_cot = False  # retained configuration field is no longer used to request reasoning
        self.thought_tag = self.cfg.get("thought_tag", "thought")

    # BETA: refine=True runs a second LLM pass — useful but doubles token usage
    def run(
        self,
        prompt: str,
        extra_system: str = "",
        refine: bool = False,
        history: list[dict] | None = None,
    ) -> KarpathyResult:
        """
        Run a prompt through the Karpathy engine.
        Returns a KarpathyResult with parsed thought and answer.
        """
        system = KARPATHY_SYSTEM
        if extra_system:
            system = f"{system}\n\nAdditional context:\n{extra_system}"

        raw = self.llm.chat(
            prompt=prompt,
            system=system,
            temperature=self.temperature,
            history=history,
        )

        result = self._parse(raw)

        if refine and result.answer:
            refined_raw = self.llm.chat(
                prompt=f"Draft to refine:\n\n{raw}",
                system=KARPATHY_REFINEMENT_SYSTEM,
                temperature=self.temperature,
            )
            result = self._parse(refined_raw)

        return result

    def self_critique(
        self,
        prompt: str,
        extra_system: str = "",
    ) -> KarpathyResult:
        """
        Two-pass critique loop: generate → critique → refine.

        Pass 1: Produce an initial answer via run().
        Pass 2: The model reads the task + its own draft and produces a
                critiqued, corrected version.

        This catches errors that single-pass generation consistently misses —
        especially hallucinations, missing edge cases, and vague claims —
        without the overhead of a full Council review.

        Returns the refined KarpathyResult. result.thought contains the
        critique reasoning; result.answer is the corrected output.
        """
        initial = self.run(prompt, extra_system=extra_system)

        critique_prompt = (
            f"Original task:\n{prompt}\n\n"
            f"Draft answer:\n{initial.answer}"
        )
        system = SELF_CRITIQUE_SYSTEM
        if extra_system:
            system = f"{system}\n\nContext:\n{extra_system}"

        raw = self.llm.chat(
            prompt=critique_prompt,
            system=system,
            temperature=self.temperature,
        )
        return self._parse(raw)

    def batch(self, prompts: list[str], **kwargs) -> list[KarpathyResult]:
        """Run multiple prompts sequentially."""
        return [self.run(p, **kwargs) for p in prompts]

    def _parse(self, raw: str) -> KarpathyResult:
        from modules.output import clean_answer
        pattern = rf"<{re.escape(self.thought_tag)}>(.*?)</{re.escape(self.thought_tag)}>"
        match = re.search(pattern, raw, re.DOTALL | re.I)
        return KarpathyResult(raw=raw, thought=match.group(1).strip() if match else "",
                              answer=clean_answer(raw, self.thought_tag),
                              had_thought_tag=bool(match))

    def build_prompt(self, task: str, examples: list[dict] | None = None) -> str:
        """
        Build a few-shot Karpathy prompt.
        examples: list of {"input": ..., "thought": ..., "output": ...}
        """
        parts = []
        if examples:
            parts.append("Examples:")
            for ex in examples:
                parts.append(
                    f"Input: {ex['input']}\n"
                    f"{ex['output']}"
                )
            parts.append("---")
        parts.append(f"Input: {task}")
        return "\n\n".join(parts)
