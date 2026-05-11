"""
agents/karpathy.py — Karpathy Patterns (The Engine)
Responsibility: Minimalist, deterministic prompting with forced chain-of-thought via <thought> tags.

New in v1.1:
  self_critique() — two-pass method where the model first produces an answer,
    then critiques it and produces a refined version. Surfaces hidden errors that
    a single-pass generation misses, without needing the full Council.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional


KARPATHY_SYSTEM = """You are a precise, minimalist reasoning engine.

Rules you MUST follow:
1. Always begin with a <thought> block. Think step-by-step before answering.
2. Inside <thought>, reason out loud: restate the problem, identify what you know,
   identify what you don't know, plan your approach.
3. After </thought>, give your final answer — clear, concise, direct.
4. Never repeat yourself. Never pad. No filler phrases.
5. If you are uncertain, say so explicitly inside <thought>. Never hallucinate.
6. Code must be complete and runnable. Prose must be factual and sourced.

Format:
<thought>
[Your reasoning here]
</thought>

[Your final answer here]
"""

KARPATHY_REFINEMENT_SYSTEM = """You are a strict output refiner.
Given a draft response, remove all filler, fix logical gaps, and tighten the prose.
Keep <thought> blocks intact. Return the refined version only.
"""

SELF_CRITIQUE_SYSTEM = """You are a self-critique agent. You will receive:
  1. The original task
  2. A draft answer

Your job:
  A. Inside <thought>, identify every flaw, gap, or unsupported claim in the draft.
     Be brutally honest. Note: logic errors, missing edge cases, hallucinations,
     vague language, unsubstantiated claims.
  B. After </thought>, write a corrected, improved version that fixes all issues you found.

If the draft is already correct, say so inside <thought> and return it unchanged.
"""


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
    - Forced <thought> chain-of-thought
    - Low temperature (deterministic)
    - Optional refinement pass
    - self_critique(): two-pass critique → refine loop
    """

    def __init__(self, llm_client, config: Optional[dict] = None):
        self.llm = llm_client
        self.cfg = config or {}
        self.temperature = self.cfg.get("temperature_override", 0.1)
        self.force_cot = self.cfg.get("force_cot", True)
        self.thought_tag = self.cfg.get("thought_tag", "thought")

    # BETA: refine=True runs a second LLM pass — useful but doubles token usage
    def run(
        self,
        prompt: str,
        extra_system: str = "",
        refine: bool = False,
        history: Optional[list[dict]] = None,
    ) -> KarpathyResult:
        """
        Run a prompt through the Karpathy engine.
        Returns a KarpathyResult with parsed thought and answer.
        """
        system = KARPATHY_SYSTEM
        if extra_system:
            system = f"{system}\n\nAdditional context:\n{extra_system}"

        if self.force_cot and "<thought>" not in prompt:
            prompt = (
                f"{prompt}\n\n"
                f"Remember: begin your reply with <{self.thought_tag}> reasoning, "
                f"then give your final answer after </{self.thought_tag}>."
            )

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
        tag = self.thought_tag
        pattern = rf"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            thought = match.group(1).strip()
            answer = raw[match.end():].strip()
            had_tag = True
        else:
            thought = ""
            answer = raw.strip()
            had_tag = False
        return KarpathyResult(raw=raw, thought=thought, answer=answer, had_thought_tag=had_tag)

    def build_prompt(self, task: str, examples: Optional[list[dict]] = None) -> str:
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
                    f"<thought>\n{ex['thought']}\n</thought>\n"
                    f"{ex['output']}"
                )
            parts.append("---")
        parts.append(f"Input: {task}")
        return "\n\n".join(parts)
