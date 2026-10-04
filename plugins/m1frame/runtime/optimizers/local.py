"""
optimizers/local.py — a dependency-free implementation of SkillOpt's core mechanic.

Microsoft's SkillOpt (https://github.com/microsoft/SkillOpt, MIT) treats a skill
document as trainable state: it proposes *bounded edits* — add, delete, replace —
to the text, scores each candidate on a held-out set, and keeps an edit only when
it improves validation performance. No weights are touched; the artefact is a
compact markdown file.

That mechanic needs no LLM to be real. This module implements it directly as a
seeded hill-climber over skill text, so m1frame gets a genuinely working optimiser
with zero dependencies, and gets the full reflective loop when someone installs the
real package (see optimizers/skillopt.py).

What this is **not**: it is not SkillOpt. It does not do LLM-generated reflective
edits, it has no benchmark suite, and it will not reproduce the paper's numbers.
It is the accept-on-improvement search loop, honestly scoped.

Guarantees, all test-pinned:
  • Deterministic under a seed — same seed, same result, no global RNG touched.
  • Never returns text scoring lower (under the same scorer) than the input.
  • A scorer that raises is treated as a rejected candidate, never a crash.
"""
from __future__ import annotations

import random
import re
from collections.abc import Callable
from dataclasses import dataclass, field

Scorer = Callable[[str], float]

MAX_UNITS = 40          # a skill document stays compact (SkillOpt: 300–2000 tokens)
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _units(text: str) -> list[str]:
    """Split skill text into edit units (sentences / lines)."""
    return [u.strip() for u in _SPLIT.split(text or "") if u.strip()]


def _join(units: list[str]) -> str:
    return " ".join(units)


@dataclass
class Edit:
    op: str                 # add | delete | replace
    index: int
    before: str = ""
    after: str = ""
    delta: float = 0.0
    accepted: bool = False

    def to_dict(self) -> dict:
        return {"op": self.op, "index": self.index, "before": self.before[:120],
                "after": self.after[:120], "delta": round(self.delta, 6),
                "accepted": self.accepted}


@dataclass
class OptimizeResult:
    tier: str                                   # local | skillopt
    before: str = ""
    after: str = ""
    before_score: float = 0.0
    after_score: float = 0.0
    rounds: int = 0
    accepted: int = 0
    history: list[Edit] = field(default_factory=list)
    error: str = ""

    @property
    def improved(self) -> bool:
        return self.after_score > self.before_score

    def to_dict(self) -> dict:
        return {"tier": self.tier, "before": self.before, "after": self.after,
                "before_score": round(self.before_score, 6),
                "after_score": round(self.after_score, 6),
                "rounds": self.rounds, "accepted": self.accepted,
                "improved": self.improved, "error": self.error,
                "history": [e.to_dict() for e in self.history]}

    def signature(self) -> tuple:
        """Determinism fingerprint — excludes every wall-clock field by construction."""
        return (self.after, round(self.after_score, 9), self.accepted,
                tuple((e.op, e.index, e.accepted) for e in self.history))


class LocalOptimizer:
    """Seeded hill-climber over skill text: propose a bounded edit, keep it if it scores better."""

    tier = "local"

    def __init__(self, seed: int = 1337, candidate_pool: list[str] | None = None) -> None:
        self.seed = int(seed)
        # Phrases the optimiser may splice in. Domain-neutral scaffolding, not content:
        # the scorer decides what earns its place.
        self.pool = candidate_pool if candidate_pool is not None else [
            "State the acceptance criteria before starting.",
            "Prefer the cheap experiment before the expensive commitment.",
            "Ground every claim in something that was actually run.",
            "Name the assumption that would falsify this.",
            "Check prior decisions before re-deriving them.",
            "Report failures as plainly as successes.",
        ]

    @staticmethod
    def _safe_score(scorer: Scorer, text: str) -> float:
        """A scorer that raises marks the candidate unusable — it never kills the run."""
        try:
            return float(scorer(text))
        except Exception:      # noqa: BLE001
            return float("-inf")

    def optimize(self, text: str, scorer: Scorer, rounds: int = 12) -> OptimizeResult:
        rng = random.Random(self.seed)          # never the global RNG — other code reseeds it
        base = (text or "").strip()
        best = base
        best_score = self._safe_score(scorer, base)
        if best_score == float("-inf"):
            return OptimizeResult(self.tier, base, base, 0.0, 0.0, 0, 0, [],
                                  error="scorer failed on the input text")

        history: list[Edit] = []
        accepted = 0
        for _ in range(max(0, int(rounds))):
            units = _units(best)
            ops = ["add"]
            if units:
                ops += ["delete", "replace"]
            op = rng.choice(ops)

            if op == "add" and len(units) < MAX_UNITS:
                idx = rng.randint(0, len(units))
                phrase = rng.choice(self.pool)
                cand_units = units[:idx] + [phrase] + units[idx:]
                edit = Edit("add", idx, after=phrase)
            elif op == "delete" and len(units) > 1:
                idx = rng.randrange(len(units))
                cand_units = units[:idx] + units[idx + 1:]
                edit = Edit("delete", idx, before=units[idx])
            elif op == "replace" and units:
                idx = rng.randrange(len(units))
                phrase = rng.choice(self.pool)
                cand_units = list(units)
                cand_units[idx] = phrase
                edit = Edit("replace", idx, before=units[idx], after=phrase)
            else:
                continue

            cand = _join(cand_units)
            score = self._safe_score(scorer, cand)
            edit.delta = 0.0 if score == float("-inf") else score - best_score
            if score > best_score:              # strict improvement only — no drift on ties
                best, best_score, edit.accepted = cand, score, True
                accepted += 1
            history.append(edit)

        return OptimizeResult(self.tier, base, best, self._safe_score(scorer, base),
                              best_score, len(history), accepted, history)
