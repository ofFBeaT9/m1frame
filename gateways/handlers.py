"""
gateways/handlers.py — the default m1frame handler for gateway messages.

`grounded_answer()` answers from the live knowledge graph with citations and no
LLM — so a gateway is useful even fully offline. `make_default_handler()` wires
plain messages to grounded chat and `/run` to a real pipeline run (when a runner
is supplied by the API server).
"""
from __future__ import annotations

import re
from typing import Callable, Optional

from .router import InboundMessage


def grounded_answer(text: str, max_pages: int = 3) -> str:
    """Keyword-grounded answer over the wiki pages, with a citation line."""
    try:
        from studio.data import wiki_pages
        pages = wiki_pages()
    except Exception:
        pages = []
    qs = {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2}
    scored = []
    for p in pages:
        hay = (p.get("title", "") + " " + (p.get("body", "") or "")).lower()
        s = sum(hay.count(w) for w in qs)
        if s:
            scored.append((s, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return "No grounded match in the knowledge graph yet. Try /run <goal> to build one."
    lines = []
    for _, p in scored[:max_pages]:
        first = next((l.strip() for l in (p.get("body", "") or "").splitlines()
                      if l.strip() and not l.strip().startswith(("#", "-", "|", ">"))), "")
        lines.append(f"• {p.get('title')}: {first}".rstrip(": ").strip())
    cites = ", ".join(p.get("title") for _, p in scored[:max_pages])
    return "\n".join(lines) + f"\n[grounded in: {cites}]"


def make_default_handler(run_async: Optional[Callable[[str], str]] = None
                         ) -> Callable[[InboundMessage], str]:
    def handler(msg: InboundMessage) -> str:
        if (msg.meta or {}).get("mode") == "run":
            if run_async is not None:
                rid = run_async(msg.text)
                return (f"▸ started a 7-pillar deliberation on:\n  “{msg.text}”\n"
                        f"run id: {rid} — watch it live in Studio.")
            return "Run mode needs the API server (start: python api/server.py), then POST /run."
        return grounded_answer(msg.text)
    return handler
