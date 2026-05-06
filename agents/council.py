"""
agents/council.py — LLM Council (The QA Gate)
Based on: github.com/gcpdev/llm-council-skill

Two distinct modes (the actual gcpdev pattern):

  Mode 1 — brainstorm(task):
    Consult personas BEFORE generating anything. Each persona analyses
    the task independently. A Synthesiser produces a unified plan.
    Use this to get a better implementation plan before code or prose.

  Mode 2 — review(task, output):
    QA gate AFTER generation. Same personas review the output.
    Synthesiser produces a consensus verdict (score 1-10).
    Score >= threshold (default 7) → approved_output is returned.

Key fix from audit: output is passed in the USER message, not the system
prompt — prevents system-prompt overflow on large outputs.
"""

from __future__ import annotations
import re
import json
from dataclasses import dataclass, field
from typing import Optional


# ── Prompts ───────────────────────────────────────────────────────────────────

BRAINSTORM_PERSONA_SYSTEM = """You are {name}, a council member in a pre-generation brainstorm.
Your role: {role}

Analyse the task BEFORE any implementation begins. Be specific and opinionated.
Highlight risks and opportunities others might miss.

Respond ONLY in this JSON (no preamble, no fences):
{{
  "persona": "{name}",
  "approach": "...",
  "key_considerations": ["...", "..."],
  "risks": ["..."],
  "opportunities": ["..."],
  "recommended_direction": "..."
}}"""

BRAINSTORM_SYNTHESIS_SYSTEM = """You are the LLM Council Synthesiser.
Multiple AI personas have brainstormed independently on a task.
Read all perspectives, find consensus, resolve conflicts, and produce one optimal plan.

Respond ONLY in this JSON (no preamble, no fences):
{
  "consensus_points": ["..."],
  "key_disagreements": ["..."],
  "recommended_plan": "...",
  "implementation_steps": ["..."],
  "risks_to_mitigate": ["..."],
  "confidence": "high|medium|low"
}"""

REVIEW_PERSONA_SYSTEM = """You are {name}, a council reviewer.
Your role: {role}

You will receive the original task and the output to review in the user message.
Assess the output critically and specifically. Cite exact issues.

Respond ONLY in this JSON (no preamble, no fences):
{{
  "persona": "{name}",
  "verdict": "pass|fail|conditional",
  "score": <integer 1-10>,
  "key_points": ["...", "..."],
  "recommendation": "..."
}}"""

REVIEW_SYNTHESIS_SYSTEM = """You are the Council Synthesiser in review mode.
You will receive individual persona assessments in the user message.
Weigh them, resolve conflicts, and produce the final consensus verdict.
If the output needs fixes, provide the corrected version in approved_output.

Respond ONLY in this JSON (no preamble, no fences):
{
  "consensus_score": <float 1-10>,
  "verdict": "pass|fail|conditional",
  "summary": "...",
  "required_fixes": ["..."],
  "approved_output": "..."
}"""


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class BrainstormPerspective:
    persona: str
    approach: str
    key_considerations: list[str]
    risks: list[str]
    opportunities: list[str]
    recommended_direction: str
    raw: str = ""


@dataclass
class BrainstormResult:
    consensus_points: list[str]
    key_disagreements: list[str]
    recommended_plan: str
    implementation_steps: list[str]
    risks_to_mitigate: list[str]
    confidence: str
    perspectives: list[BrainstormPerspective] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Council Brainstorm  [confidence: {self.confidence}]",
            f"Plan: {self.recommended_plan}",
        ]
        for i, step in enumerate(self.implementation_steps, 1):
            lines.append(f"  {i}. {step}")
        if self.risks_to_mitigate:
            lines.append("Risks: " + "; ".join(self.risks_to_mitigate))
        return "\n".join(lines)


@dataclass
class PersonaAssessment:
    persona: str
    verdict: str        # pass | fail | conditional
    score: int
    key_points: list[str]
    recommendation: str
    raw: str = ""


@dataclass
class CouncilVerdict:
    consensus_score: float
    verdict: str        # pass | fail | conditional
    summary: str
    required_fixes: list[str]
    approved_output: str
    assessments: list[PersonaAssessment] = field(default_factory=list)
    passed: bool = False

    def __post_init__(self) -> None:
        self.passed = (self.verdict == "pass" and self.consensus_score >= 7.0)

    def report(self) -> str:
        lines = [
            f"Council Verdict: {self.verdict.upper()}  (score {self.consensus_score:.1f}/10)",
            f"Summary: {self.summary}",
        ]
        if self.required_fixes:
            lines.append("Required fixes:")
            for fix in self.required_fixes:
                lines.append(f"  • {fix}")
        lines.append(f"Passed QA gate: {self.passed}")
        return "\n".join(lines)


# ── Main class ────────────────────────────────────────────────────────────────

class LLMCouncil:
    """
    LLM Council — pre-generation brainstorm + post-generation QA review.

    Default personas: Critic, Advocate, Domain Expert.
    (Synthesiser is a separate aggregation step, not a debating persona.)
    """

    DEFAULT_PERSONAS = [
        {
            "name": "Critic",
            "role": "Find logical flaws, hallucinations, missing edge cases, and unsupported claims. Be rigorous.",
        },
        {
            "name": "Advocate",
            "role": "Defend the strongest approach. Highlight what is working and why the output is sound.",
        },
        {
            "name": "Domain Expert",
            "role": "Apply deep technical knowledge. Flag domain-specific risks, best practices, and anti-patterns.",
        },
    ]

    def __init__(self, llm_client, config: Optional[dict] = None) -> None:
        self.llm = llm_client
        self.cfg = config or {}
        self.personas = self.cfg.get("personas", self.DEFAULT_PERSONAS)
        self.threshold = float(self.cfg.get("consensus_threshold", 7.0))
        self.max_rounds = int(self.cfg.get("max_debate_rounds", 2))

    # ── Mode 1: Brainstorm ────────────────────────────────────────────────────

    def brainstorm(self, task: str) -> BrainstormResult:
        """
        Run council BEFORE generating output (gcpdev pattern).
        Each persona analyses the task independently, then a Synthesiser
        produces one unified implementation plan.
        """
        perspectives = [self._brainstorm_persona(p, task) for p in self.personas]
        result = self._synthesise_brainstorm(task, perspectives)
        result.perspectives = perspectives
        return result

    # ── Mode 2: Review ────────────────────────────────────────────────────────

    def review(self, task: str, output: str, _round: int = 1) -> CouncilVerdict:
        """
        QA gate AFTER generation.
        Returns a CouncilVerdict; verdict.approved_output is the final text to use.
        _round is internal — controls the retry limit.
        """
        assessments = [self._review_persona(p, task, output) for p in self.personas]
        verdict = self._synthesise_review(task, output, assessments)
        verdict.assessments = assessments

        # One optional retry on the corrected output — strictly limited
        if not verdict.passed and _round < self.max_rounds:
            return self.review(task, verdict.approved_output, _round=_round + 1)

        return verdict

    def quick_check(self, task: str, output: str) -> bool:
        """Return True if output passes the council QA gate."""
        return self.review(task, output).passed

    # ── Private: brainstorm ───────────────────────────────────────────────────

    def _brainstorm_persona(self, persona: dict, task: str) -> BrainstormPerspective:
        system = BRAINSTORM_PERSONA_SYSTEM.format(
            name=persona["name"], role=persona["role"]
        )
        # Task goes in user message — keeps system prompt clean
        raw = self.llm.chat(
            prompt=f"Task to brainstorm:\n\n{task}",
            system=system,
            temperature=0.4,
        )
        try:
            d = _parse_json(raw)
            return BrainstormPerspective(
                persona=d.get("persona", persona["name"]),
                approach=d.get("approach", ""),
                key_considerations=d.get("key_considerations", []),
                risks=d.get("risks", []),
                opportunities=d.get("opportunities", []),
                recommended_direction=d.get("recommended_direction", ""),
                raw=raw,
            )
        except (ValueError, KeyError):
            return BrainstormPerspective(
                persona=persona["name"], approach=raw[:200],
                key_considerations=[], risks=[], opportunities=[],
                recommended_direction="", raw=raw,
            )

    def _synthesise_brainstorm(self, task: str, perspectives: list[BrainstormPerspective]) -> BrainstormResult:
        parts = "\n\n".join(
            f"{p.persona}:\n"
            f"  Approach: {p.approach}\n"
            f"  Considerations: {'; '.join(p.key_considerations)}\n"
            f"  Risks: {'; '.join(p.risks)}\n"
            f"  Direction: {p.recommended_direction}"
            for p in perspectives
        )
        prompt = f"Task: {task}\n\nPersona perspectives:\n\n{parts}"
        raw = self.llm.chat(prompt=prompt, system=BRAINSTORM_SYNTHESIS_SYSTEM, temperature=0.2)
        try:
            d = _parse_json(raw)
            return BrainstormResult(
                consensus_points=d.get("consensus_points", []),
                key_disagreements=d.get("key_disagreements", []),
                recommended_plan=d.get("recommended_plan", ""),
                implementation_steps=d.get("implementation_steps", []),
                risks_to_mitigate=d.get("risks_to_mitigate", []),
                confidence=d.get("confidence", "medium"),
            )
        except ValueError:
            return BrainstormResult(
                consensus_points=[], key_disagreements=[],
                recommended_plan=raw[:300], implementation_steps=[],
                risks_to_mitigate=[], confidence="low",
            )

    # ── Private: review ───────────────────────────────────────────────────────

    def _review_persona(self, persona: dict, task: str, output: str) -> PersonaAssessment:
        system = REVIEW_PERSONA_SYSTEM.format(name=persona["name"], role=persona["role"])
        # Output goes in user message — avoids system prompt overflow on long outputs
        prompt = f"Original task:\n{task}\n\nOutput to review:\n{output}"
        raw = self.llm.chat(prompt=prompt, system=system, temperature=0.3)
        try:
            d = _parse_json(raw)
            return PersonaAssessment(
                persona=d.get("persona", persona["name"]),
                verdict=d.get("verdict", "conditional"),
                score=int(d.get("score", 5)),
                key_points=d.get("key_points", []),
                recommendation=d.get("recommendation", ""),
                raw=raw,
            )
        except (ValueError, KeyError):
            return PersonaAssessment(
                persona=persona["name"], verdict="conditional",
                score=5, key_points=["Parse error — review manually"],
                recommendation=raw[:300], raw=raw,
            )

    def _synthesise_review(self, task: str, output: str, assessments: list[PersonaAssessment]) -> CouncilVerdict:
        assessment_text = "\n\n".join(
            f"{a.persona}: verdict={a.verdict}, score={a.score}/10\n"
            f"  Points: {'; '.join(a.key_points)}\n"
            f"  Recommendation: {a.recommendation}"
            for a in assessments
        )
        prompt = (
            f"Task: {task}\n\n"
            f"Output being reviewed (first 2000 chars):\n{output[:2000]}\n\n"
            f"Individual assessments:\n{assessment_text}"
        )
        raw = self.llm.chat(prompt=prompt, system=REVIEW_SYNTHESIS_SYSTEM, temperature=0.2)
        try:
            d = _parse_json(raw)
            return CouncilVerdict(
                consensus_score=float(d.get("consensus_score", 5)),
                verdict=d.get("verdict", "conditional"),
                summary=d.get("summary", ""),
                required_fixes=d.get("required_fixes", []),
                approved_output=d.get("approved_output", output),
            )
        except ValueError:
            avg = sum(a.score for a in assessments) / max(len(assessments), 1)
            return CouncilVerdict(
                consensus_score=avg,
                verdict="conditional" if avg >= self.threshold else "fail",
                summary="Synthesiser parse error — falling back to score average.",
                required_fixes=["Re-run council for a structured verdict."],
                approved_output=output,
            )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    """Strip markdown fences and parse JSON. Raises ValueError on failure."""
    clean = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse failed: {exc}\nRaw text:\n{text[:400]}") from exc
