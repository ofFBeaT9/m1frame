"""
studio/data.py — read-only views over the repo for the Studio API.

Pure-Python, no LLM, no network. Powers the Graph, Wiki, Memory, and Settings
surfaces (and grounded chat in demo mode) by parsing the same files the rest of
m1frame already maintains: the `wiki/` knowledge graph and the exported miras
snapshot. Mirrors the wiki-parsing approach in `m1frame/build_dashboard.py`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
STRUCTURAL = {"index", "log", "overview", "purpose"}
_LINK = re.compile(r"\[\[([^\]|]+)")
_FRONTMATTER = re.compile(r"^---.*?---", re.S)


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER.sub("", text, count=1).strip()


def _pages() -> list[dict]:
    """Parse every non-structural wiki page → list of rich page dicts."""
    out = []
    for p in sorted(WIKI.rglob("*.md")):
        if p.stem in STRUCTURAL:
            continue
        text = p.read_text(encoding="utf-8")
        mt = re.search(r"^title:\s*(.+)$", text, re.M)
        if not mt:
            continue
        pt = re.search(r"^page_type:\s*(.+)$", text, re.M)
        tags = re.search(r"^tags:\s*\[(.*)\]", text, re.M)
        conf = re.search(r"^confidence:\s*(.+)$", text, re.M)
        out.append({
            "title": mt.group(1).strip(),
            "type": pt.group(1).strip() if pt else "page",
            "tags": [t.strip().strip('"\'') for t in (tags.group(1).split(",") if tags else []) if t.strip()],
            "confidence": conf.group(1).strip() if conf else "",
            "file": str(p.relative_to(ROOT)).replace("\\", "/"),
            "links": [ln.strip() for ln in _LINK.findall(text)],
            "body": _strip_frontmatter(text),
        })
    return out


def wiki_pages() -> list[dict]:
    """Pages with body, for the Wiki reader (drops the internal `links` field)."""
    return [{k: v for k, v in p.items() if k != "links"} for p in _pages()]


def wiki_graph() -> dict:
    """Force-directed graph data: nodes (titled pages) + de-duped wikilink edges."""
    pages = _pages()
    ids = {p["title"] for p in pages}
    nodes = [{"id": p["title"], "type": p["type"], "file": p["file"]} for p in pages]
    links, seen = [], set()
    for p in pages:
        for tgt in p["links"]:
            if tgt in ids and tgt != p["title"]:
                key = tuple(sorted((p["title"], tgt)))
                if key not in seen:
                    seen.add(key)
                    links.append({"source": p["title"], "target": tgt})
    return {"nodes": nodes, "links": links}


def load_memories() -> list[dict]:
    """miras memories from the exported snapshot (m1frame/miras_snapshot.json)."""
    f = ROOT / "m1frame" / "miras_snapshot.json"
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []
    mems = data.get("memories", data) if isinstance(data, dict) else data
    out = []
    for m in (mems if isinstance(mems, list) else []):
        if not isinstance(m, dict):
            continue
        c = str(m.get("content", ""))
        out.append({
            "type": m.get("content_type", m.get("type", "memory")),
            "agent": m.get("source_agent", m.get("agent", "")),
            "tags": m.get("tags", ""),
            "weight": m.get("weight"),
            "text": c[:400] + ("…" if len(c) > 400 else ""),
        })
    return out


def keyword_answer(question: str, k: int = 3) -> dict:
    """Grounded answer with no LLM — keyword-rank wiki pages and quote them.

    Used by `/chat` and `/wiki/query` when no API key is present, so the Chat and
    Wiki surfaces stay useful in demo mode.
    """
    pages = _pages()
    qwords = {w for w in re.findall(r"[a-z0-9]+", question.lower()) if len(w) > 2}
    scored = []
    for p in pages:
        hay = (p["title"] + " " + p["body"]).lower()
        score = sum(hay.count(w) for w in qwords)
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    top = [p for _, p in scored[:k]]
    if not top:
        return {"answer": "No grounded match in the knowledge graph yet. Try a run first.",
                "citations": []}
    paras = []
    for p in top:
        first = next((ln.strip() for ln in p["body"].splitlines()
                      if ln.strip() and not ln.startswith(("#", "-", "|"))), "")
        paras.append(f"**{p['title']}** — {first}")
    return {"answer": "\n\n".join(paras), "citations": [p["title"] for p in top]}
