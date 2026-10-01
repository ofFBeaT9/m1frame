"""Offline capability inventory: python -m scripts.context_probe --query 'task'."""
from __future__ import annotations

import argparse
import json

from agents.miras import ROLE_MAP
from agents.skills import SkillLibrary
from llm_client import load_config
from modules.headroom import HeadroomAdapter
from scientific import ScientificLibrary
from tools import default_registry


def inspect_context(query: str = "", cfg: dict | None = None) -> dict:
    cfg = load_config() if cfg is None else cfg
    scfg = cfg.get("scientific") or {}
    scientific = ScientificLibrary(scfg.get("path"))
    library = SkillLibrary()
    backend = cfg.get("backend", "claude")
    return {
        "backend": backend,
        "chat_default": "full",
        "agents": ROLE_MAP,
        "tools": default_registry().list(),
        "learned_skills": [{"id": s.id, "title": s.title} for s in library.all()],
        "suggested_skills": [s.id for s in library.suggest(query)],
        "scientific": {"enabled": scfg.get("enabled", True), "count": len(scientific.skills),
                       "names": sorted(scientific.skills), "errors": scientific.errors},
        "wiki": cfg.get("wiki", {}),
        "headroom": {"policy": cfg.get("context", {}),
                     "output_reserve_tokens": cfg.get(backend, {}).get("max_tokens"),
                     "optional_adapter": HeadroomAdapter(cfg.get("headroom")).status(),
                     "host_headroom_connected": False},
        "external_miras": "Host MCP when available; not connected by the Python runtime",
        "external_mcp": "No automatic stdio connector; host MCP tools are separate",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="")
    args = parser.parse_args()
    print(json.dumps(inspect_context(args.query), indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
