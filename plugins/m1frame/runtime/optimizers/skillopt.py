"""
optimizers/skillopt.py — adapter for Microsoft SkillOpt.

Honest scope, stated up front: SkillOpt's published docs describe its CLI
(`skillopt`, `skillopt-sleep`), its WebUI, and its extension points
(`skillopt/model/<name>_backend.py`, `skillopt/envs/<name>/`) — but **no stable
public Python API**. So this adapter does not pretend to know one.

Instead of binding to a guessed interface, it *probes*: it imports the package and
walks a list of candidate entry points, reporting exactly what it found and what it
looked for. If nothing compatible turns up, `available()` is False with an
actionable reason and `SkillOptimizer` falls back to the dependency-free tier in
optimizers/local.py. A wrong guess therefore degrades to "unavailable", never to a
confident-looking call into a function that doesn't exist.

Note the import in `_probe` is the *library* `skillopt`, not this module: Python 3
absolute imports resolve `import skillopt` to the installed package even from a
module of the same name inside a package. m1frame deliberately does not have a
repo-root `skillopt/` directory — that would shadow the library. See sensors/ and
optimizers/ naming in studies/m1frame-modules-sentrux-skillopt/ROADMAP.md § D1.

    pip install skillopt        # optional — m1frame never requires it
"""
from __future__ import annotations

import importlib
import inspect
import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .local import Edit, LocalOptimizer, OptimizeResult, Scorer, _units

# Entry points we probe for, best-first, as `(module, attribute)`.
#
# The first two are SkillOpt's REAL edit-application API, confirmed against an
# installed skillopt 0.2.0:
#     skillopt.optimizer.apply_edit(skill: str, edit: Edit | dict) -> str
#     skillopt.optimizer.apply_patch(skill: str, patch: Patch | dict) -> str
#     skillopt.types.EditOp = Literal['append','insert_after','replace','delete']
# That is exactly the bounded-edit primitive m1frame needs: SkillOpt owns *how an
# edit is applied*, m1frame owns *which edits to try and whether to keep them*.
# The remaining names are fallbacks in case a future release moves the surface.
CANDIDATE_ENTRY_POINTS: list[tuple[str, str]] = [
    ("skillopt.optimizer", "apply_patch"),
    ("skillopt.optimizer", "apply_edit"),
    ("skillopt", "optimize"),
    ("skillopt", "optimize_skill"),
    ("skillopt", "SkillOptimizer"),
]

# SkillOpt's edit vocabulary. 'append'/'insert_after' add, so both map to our add.
SKILLOPT_OPS = ("append", "insert_after", "replace", "delete")


class SkillOptAdapter:
    """Tier-2 delegation to the real SkillOpt package, if a compatible surface exists."""

    tier = "skillopt"

    def __init__(self) -> None:
        self._entry: Callable[..., Any] | None = None
        self._entry_name: str = ""
        self._probed: list[str] = []
        self._reason: str = ""

    # ── capability probing ──────────────────────────────────────────────────

    def _import(self) -> Any | None:
        try:
            return importlib.import_module("skillopt")
        except Exception:      # noqa: BLE001 — not installed, or broken install
            return None

    def probe(self) -> dict:
        """Look for a usable entry point. Idempotent; safe to call when nothing is installed."""
        self._probed = [f"{m}.{a}" for m, a in CANDIDATE_ENTRY_POINTS]
        pkg = self._import()
        if pkg is None:
            self._entry, self._entry_name = None, ""
            self._reason = ("skillopt is not installed — the dependency-free local "
                            "optimizer is in use. Install with: pip install skillopt")
            return self.status()

        # Guard against a repo-root package shadowing the library. Compare resolved
        # paths, not substrings — a string match on the checkout's directory name
        # silently stops firing the moment someone renames the checkout.
        origin = getattr(pkg, "__file__", "") or ""
        if origin:
            try:
                if Path(origin).resolve().parent == Path(__file__).resolve().parent:
                    self._entry, self._entry_name = None, ""
                    self._reason = (f"import 'skillopt' resolved to m1frame's own "
                                    f"module ({origin})")
                    return self.status()
            except Exception:  # noqa: BLE001
                pass

        for mod_name, attr in CANDIDATE_ENTRY_POINTS:
            try:
                mod = pkg if mod_name == "skillopt" else importlib.import_module(mod_name)
            except Exception:  # noqa: BLE001
                continue
            fn = getattr(mod, attr, None)
            # isroutine, not callable: a class is callable, and "probing" it would
            # mean *instantiating* a third-party class with guessed constructor
            # arguments and running whatever its __init__ does.
            if inspect.isroutine(fn):
                self._entry, self._entry_name = fn, f"{mod_name}.{attr}"
                self._reason = ""
                return self.status()

        self._entry, self._entry_name = None, ""
        version = getattr(pkg, "__version__", "unknown")
        self._reason = (f"skillopt {version} is installed but no compatible entry point was "
                        f"found (probed: {', '.join(self._probed)}). Falling back to the local "
                        f"optimizer. Its CLI (`skillopt`) may still work standalone.")
        return self.status()

    def available(self) -> bool:
        if self._entry is None and not self._reason:
            self.probe()
        return self._entry is not None

    def status(self) -> dict:
        return {"tier": self.tier, "available": self._entry is not None,
                "entry_point": self._entry_name, "probed": list(self._probed),
                "reason": self._reason}

    # ── delegation ──────────────────────────────────────────────────────────

    def optimize(self, text: str, scorer: Scorer, rounds: int = 12,
                 seed: int = 1337, pool: list[str] | None = None) -> OptimizeResult:
        """Optimise with SkillOpt applying every edit.

        The division of labour: **SkillOpt applies the bounded edit** — its
        `apply_edit`/`apply_patch`, its `EditOp` vocabulary ('append',
        'insert_after', 'replace', 'delete') — while m1frame proposes candidates
        and runs the accept-on-improvement loop against its own scorer. Same
        guarantees as the local tier: deterministic under a seed, and never returns
        a document scoring worse than the input.
        """
        if not self.available():
            return OptimizeResult(self.tier, text, text, 0.0, 0.0, 0, 0, [],
                                  error=self._reason or "skillopt unavailable")
        apply_one = self._resolve_apply()
        if apply_one is None:
            return OptimizeResult(self.tier, text, text, 0.0, 0.0, 0, 0, [],
                                  error=f"no usable edit applier at {self._entry_name}")

        rng = random.Random(int(seed))
        phrases = pool if pool is not None else list(LocalOptimizer().pool)
        base = (text or "").strip()
        try:
            best_score = float(scorer(base))
        except Exception as e:                     # noqa: BLE001
            return OptimizeResult(self.tier, base, base, 0.0, 0.0, 0, 0, [],
                                  error=f"scorer failed on the input text: {e}")

        best, history, accepted = base, [], 0
        for _ in range(max(0, int(rounds))):
            units = _units(best)
            op = rng.choice(list(SKILLOPT_OPS) if units else ["append"])
            target = rng.choice(units) if units else ""
            content = "" if op == "delete" else rng.choice(phrases)
            try:
                cand = apply_one(best, {"op": op, "content": content, "target": target})
            except Exception:                      # noqa: BLE001 — a rejected edit, not a crash
                continue
            if not isinstance(cand, str) or not cand.strip() or cand == best:
                continue
            try:
                score = float(scorer(cand))
            except Exception:                      # noqa: BLE001
                continue
            rec = Edit(op, 0, before=target, after=content, delta=score - best_score)
            if score > best_score:                 # strict improvement only
                best, best_score, rec.accepted = cand, score, True
                accepted += 1
            history.append(rec)

        return OptimizeResult(self.tier, base, best, float(scorer(base)), best_score,
                              len(history), accepted, history)

    def _resolve_apply(self):
        """Adapt whichever entry point we found to a common `(skill, edit) -> str`."""
        fn, name = self._entry, self._entry_name
        if fn is None:
            return None
        if name.endswith("apply_edit"):
            return lambda skill, edit: fn(skill, edit)
        if name.endswith("apply_patch"):
            return lambda skill, edit: fn(skill, {"edits": [edit], "reasoning": "m1frame"})
        def generic(skill, edit):                  # unknown future surface: try once
            out = fn(skill)
            return out if isinstance(out, str) else skill
        return generic
