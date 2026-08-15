"""
optimizers/ — make m1frame's skills get better, not just accumulate.

m1frame's skill library (agents/skills.py) is write-once: a run clears the council
gate, its approach is distilled into a `Skill`, and that text is frozen forever —
then re-injected into future planning. A mediocre-but-passing run leaves a mediocre
skill that compounds.

This module closes that loop, borrowing the mechanic from Microsoft SkillOpt
(https://github.com/microsoft/SkillOpt, MIT): treat the skill document as trainable
state, propose bounded edits, keep only what measurably improves.

Two tiers, and the result always tells you which one ran:

  • `local`    — a dependency-free seeded hill-climber (optimizers/local.py).
                 Always available. Genuinely works. Not a stub.
  • `skillopt` — delegation to the real package when installed (optimizers/skillopt.py).
                 Probed, never assumed — SkillOpt publishes no stable Python API.

    from optimizers import SkillOptimizer
    r = SkillOptimizer().optimize("draft skill text", scorer=my_scorer)
    print(r.tier, r.before_score, "→", r.after_score)
"""
from __future__ import annotations

from collections.abc import Callable

from .local import Edit, LocalOptimizer, OptimizeResult, Scorer
from .skillopt import SkillOptAdapter

__all__ = ["SkillOptimizer", "LocalOptimizer", "SkillOptAdapter",
           "OptimizeResult", "Edit", "Scorer"]


class SkillOptimizer:
    """Pick the best available tier and optimise. Never raises; never returns worse text."""

    def __init__(self, seed: int = 1337, prefer: str = "auto") -> None:
        """`prefer`: 'auto' (skillopt if usable, else local) | 'local' | 'skillopt'."""
        self.seed = int(seed)
        self.prefer = str(prefer or "auto").lower()
        self.local = LocalOptimizer(seed=self.seed)
        self.remote = SkillOptAdapter()

    def status(self) -> dict:
        remote = self.remote.status() if self.remote._entry_name or self.remote._reason \
            else self.remote.probe()
        return {"prefer": self.prefer, "seed": self.seed,
                "active_tier": self.pick(), "tiers": {
                    "local": {"tier": "local", "available": True,
                              "reason": "dependency-free; always available"},
                    "skillopt": remote}}

    def pick(self) -> str:
        if self.prefer == "local":
            return "local"
        if self.prefer == "skillopt":
            return "skillopt" if self.remote.available() else "local"
        return "skillopt" if self.remote.available() else "local"

    def optimize(self, text: str, scorer: Callable[[str], float], rounds: int = 12,
                 pool: list[str] | None = None) -> OptimizeResult:
        """`pool` supplies the candidate phrases edits may splice in.

        Passing material drawn from the run itself is what makes optimisation able
        to actually improve a skill: with only the generic default pool, a scorer
        that rewards run-specific terms can never be satisfied, and every round is
        rejected.
        """
        if self.pick() == "skillopt":
            result = self.remote.optimize(text, scorer, rounds=rounds,
                                          seed=self.seed, pool=pool)
            if not result.error:
                return result
            # Tier 2 refused or failed — fall through rather than lose the request.
            fallback = LocalOptimizer(seed=self.seed, candidate_pool=pool).optimize(
                text, scorer, rounds=rounds)
            fallback.error = f"skillopt tier unavailable ({result.error}); used local"
            return fallback
        opt = LocalOptimizer(seed=self.seed, candidate_pool=pool) if pool else self.local
        return opt.optimize(text, scorer, rounds=rounds)
