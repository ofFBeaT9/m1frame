"""
optimizers/tools.py — expose skill optimisation on m1frame's tool surface.

A tool call arrives as JSON, so it cannot carry a Python callable. The scorer is
therefore built here from declarative arguments: cover these `keywords`, stay short.
It is deliberately simple and fully auditable — you can read it in ten seconds and
predict exactly what it will reward, which is the point of m1frame's tool surface.

    skill_optimize(text="...", keywords=["falsifiable","cheap experiment"])
"""
from __future__ import annotations

from collections.abc import Callable

from . import SkillOptimizer

LENGTH_PENALTY = 0.02      # per word — keeps an optimised skill compact


def keyword_scorer(keywords: list[str],
                   length_penalty: float = LENGTH_PENALTY) -> Callable[[str], float]:
    """Reward covering each keyword once; penalise every word of length."""
    kws = [str(k).lower().strip() for k in (keywords or []) if str(k).strip()]

    def score(text: str) -> float:
        low = (text or "").lower()
        return sum(1.0 for k in kws if k in low) - length_penalty * len(low.split())
    return score


def optimizer_config() -> dict:
    """`optimizers:` from config.yaml, with safe defaults. Never raises.

    One config read shared by every surface — the HTTP route, the ToolRegistry
    tool and the MCP tool must not disagree about seed/prefer/rounds.
    """
    defaults = {"enabled": True, "prefer": "auto", "rounds": 12, "seed": 1337}
    try:
        from llm_client import load_config
        cfg = (load_config() or {}).get("optimizers") or {}
    except Exception:      # noqa: BLE001
        cfg = {}
    return {**defaults, **{k: v for k, v in cfg.items() if k in defaults}}


def optimizer(seed: int | None = None, prefer: str | None = None) -> SkillOptimizer:
    """A config-honouring SkillOptimizer — the single constructor all surfaces use."""
    c = optimizer_config()
    return SkillOptimizer(seed=int(c["seed"] if seed is None else seed),
                          prefer=str(c["prefer"] if prefer is None else prefer))


def optimizer_status() -> dict:
    """Which optimisation tier is active, and why."""
    st = optimizer().status()
    st["enabled"] = bool(optimizer_config()["enabled"])
    return st


MAX_ROUNDS = 500          # the loop is O(rounds x len(text)) and runs synchronously
MAX_TEXT = 100_000        # a skill document is meant to be compact, not a corpus


def skill_optimize(text: str, keywords: list[str] | None = None,
                   rounds: int | None = None, seed: int | None = None,
                   prefer: str | None = None) -> dict:
    """Optimise skill text so it covers `keywords` concisely. Never returns worse text.

    Inputs are clamped here rather than only at the HTTP layer, because this same
    function is reachable through `POST /tools/call` and the MCP server.
    """
    c = optimizer_config()
    try:
        n = int(c["rounds"] if rounds is None else rounds)
    except Exception:     # noqa: BLE001
        n = int(c["rounds"])
    return optimizer(seed, prefer).optimize(
        str(text or "")[:MAX_TEXT], keyword_scorer((keywords or [])[:64]),
        rounds=max(0, min(MAX_ROUNDS, n))).to_dict()


def register_optimizer_tools(reg):
    """Register the optimizer tools into a ToolRegistry."""
    from tools.registry import Tool
    reg.register(Tool("optimizer_status", "Which skill-optimisation tier is active (local|skillopt).",
                      optimizer_status, {}))
    reg.register(Tool("skill_optimize", "Improve skill text against keyword coverage, concisely.",
                      skill_optimize, {"text": "string", "keywords": "list[string]",
                                       "rounds": "int (optional)", "seed": "int (optional)",
                                       "prefer": "auto|local|skillopt (optional)"}))
    return reg
