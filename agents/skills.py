"""
agents/skills.py — the council-vetted skill-learning loop.

m1frame's answer to a self-improving agent, with a twist Hermes can't match:
**only deliberation-vetted recipes are remembered.** When a run clears the
Council QA gate (consensus ≥ threshold), the *approach* that worked — its BMAD
story shape, roles, and summary — is distilled into a reusable `Skill`. On the
next similar goal, `suggest()` surfaces those skills to seed planning, so the
system gets faster and better over time. Every skill is auditable: it records
the goal it came from, the score that earned it, and how often it's been reused.

Dependency-free (json + pathlib). The store is a plain JSON file you can read,
diff, and version in git — zero lock-in, like the rest of m1frame.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Small stopword set so keyword matching focuses on the meaningful terms.
_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "for", "with", "in", "on", "at",
    "is", "are", "be", "this", "that", "from", "into", "as", "by", "it", "we",
    "build", "make", "create", "add", "using", "use", "write", "design", "should",
    "how", "what", "why", "can", "your", "you", "our",
}


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    seen, out = set(), []
    for w in words:
        if len(w) > 2 and w not in _STOP and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def _overlap(a: list[str], b: list[str]) -> float:
    """Fraction of the query's keywords present in the candidate (0..1)."""
    if not a:
        return 0.0
    bs = set(b)
    return sum(1 for w in a if w in bs) / len(a)


@dataclass
class Skill:
    """A reusable, council-vetted recipe distilled from a successful run."""
    id: str
    title: str
    goal: str
    domain: str
    keywords: list[str]
    roles: list[str]
    steps: list[str]
    approach: str
    score: float
    uses: int = 0
    created: str = field(default_factory=lambda: time.strftime("%Y-%m-%d"))
    last_used: str = ""

    def summary(self) -> str:
        return (f"{self.title} (used {self.uses}×, vetted {self.score:.1f}/10) — "
                f"{self.approach[:160]}")


class SkillLibrary:
    """Load/save council-vetted skills; learn from passes; suggest on new goals."""

    def __init__(self, path: str = "skills/skills.json", threshold: float = 7.0) -> None:
        self.path = Path(path)
        self.threshold = float(threshold)
        self.skills: list[Skill] = self._load()

    # ── persistence ─────────────────────────────────────────────────────────

    def _load(self) -> list[Skill]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []
        items = raw.get("skills", raw) if isinstance(raw, dict) else raw
        out = []
        for d in (items if isinstance(items, list) else []):
            if not (isinstance(d, dict) and d.get("id")):
                continue
            # Tolerate partial / hand-edited entries: never pass None into a typed field.
            out.append(Skill(
                id=str(d["id"]), title=d.get("title") or "", goal=d.get("goal") or "",
                domain=d.get("domain") or "general",
                keywords=d.get("keywords") or _keywords(d.get("goal", "")),
                roles=d.get("roles") or [], steps=d.get("steps") or [],
                approach=d.get("approach") or "", score=float(d.get("score") or 0),
                uses=int(d.get("uses") or 0), created=d.get("created") or "",
                last_used=d.get("last_used") or ""))
        return out

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "updated": time.strftime("%Y-%m-%d %H:%M"),
                   "skills": [asdict(s) for s in self.skills]}
        # Atomic write: a crash or concurrent run can't leave a half-written store.
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    # ── query ───────────────────────────────────────────────────────────────

    def all(self) -> list[Skill]:
        """Skills ranked by reinforcement (uses) then vetted score."""
        return sorted(self.skills, key=lambda s: (s.uses, s.score), reverse=True)

    def suggest(self, goal: str, k: int = 3, min_overlap: float = 0.34) -> list[Skill]:
        """Prior vetted skills whose goal keywords overlap this goal."""
        qk = _keywords(goal)
        scored = [(s, _overlap(qk, s.keywords)) for s in self.skills]
        hits = sorted([(s, o) for s, o in scored if o >= min_overlap],
                      key=lambda x: (x[1], x[0].uses, x[0].score), reverse=True)
        return [s for s, _ in hits[:k]]

    def as_context(self, skills: list[Skill]) -> str:
        """Render suggested skills for injection into BMAD planning context."""
        if not skills:
            return ""
        lines = ["Prior council-vetted approaches for similar goals (reuse what fits):"]
        for s in skills:
            lines.append(f"- {s.title}: {s.approach[:200]} [roles: {', '.join(s.roles)}]")
        return "\n".join(lines)

    # ── learning ────────────────────────────────────────────────────────────

    def learn(self, goal: str, blueprint, score: float,
              approach: str = "") -> Skill | None:
        """Distil a vetted skill from a passing run. Returns the Skill, or None
        if the score didn't clear the gate. Near-duplicate goals reinforce the
        existing skill instead of creating a new one.
        """
        if score is None or float(score) < self.threshold:
            return None  # not vetted — m1frame only remembers what the council passed
        qk = _keywords(goal)

        # Reinforce a near-duplicate rather than fragmenting the library.
        for s in self.skills:
            if _overlap(qk, s.keywords) >= 0.7:
                s.uses += 1
                s.score = max(s.score, float(score))
                s.last_used = time.strftime("%Y-%m-%d")
                self.save()
                return s

        stories = getattr(blueprint, "stories", []) or []
        skill = Skill(
            id=uuid.uuid4().hex[:8],
            title=getattr(blueprint, "project_name", "") or goal[:60],
            goal=goal,
            domain=getattr(blueprint, "domain", "general"),
            keywords=qk,
            roles=list(dict.fromkeys(getattr(s, "role", "dev") for s in stories)),
            steps=[getattr(s, "title", "") for s in stories][:8],
            approach=approach or getattr(blueprint, "mvp_scope", "") or "",
            score=float(score),
            uses=1,
            last_used=time.strftime("%Y-%m-%d"),
        )
        self.skills.append(skill)
        self.save()
        return skill

    # ── optimisation ────────────────────────────────────────────────────────

    def optimize_skill(self, skill_id: str, scorer, rounds: int = 12,
                       seed: int = 1337, prefer: str = "auto",
                       pool: list[str] | None = None):
        """Improve a stored skill's `approach` text and persist it.

        This is the half `learn()` never had: learning remembers what passed,
        optimisation makes it better. Returns the optimiser's result dict, or a
        dict with `error` — it never raises, so a bad scorer can't corrupt the
        store or kill a run (same contract as the rest of the skill loop).
        """
        skill = next((s for s in self.skills if s.id == skill_id), None)
        if skill is None:
            return {"error": f"unknown skill '{skill_id}'"}
        try:
            from optimizers import SkillOptimizer
            result = SkillOptimizer(seed=seed, prefer=prefer).optimize(
                skill.approach, scorer, rounds=rounds, pool=pool)
        except Exception as e:      # noqa: BLE001 — optimisation is best-effort, always
            return {"error": f"optimizer unavailable: {e}"}
        # Only persist a strict improvement; ties leave the store untouched.
        if result.improved and result.after and result.after != skill.approach:
            skill.approach = result.after
            self.save()
        out = result.to_dict()
        out["persisted"] = bool(result.improved and result.after != result.before)
        out["skill_id"] = skill_id
        return out

    def reinforce(self, skill_id: str) -> bool:
        for s in self.skills:
            if s.id == skill_id:
                s.uses += 1
                s.last_used = time.strftime("%Y-%m-%d")
                self.save()
                return True
        return False

    def remove(self, skill_id: str) -> bool:
        n = len(self.skills)
        self.skills = [s for s in self.skills if s.id != skill_id]
        if len(self.skills) != n:
            self.save()
            return True
        return False
