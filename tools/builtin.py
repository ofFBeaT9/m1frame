"""
tools/builtin.py — the safe, offline tools m1frame ships with.

Deliberately small and *auditable* rather than "40+ tools" of unknown provenance:
a safe calculator (AST-evaluated, no eval), knowledge-graph search, datetime, word
count, and an SSRF-guarded HTTP GET. Extend by registering your own, or attach an
MCP server (tools/mcp_client.py). Every tool here runs with no network except the
explicitly-guarded fetch.
"""
from __future__ import annotations

import ast
import operator
import re
import time

from .registry import Tool, ToolRegistry

# ── safe arithmetic (no eval, no names, no calls) ─────────────────────────────
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


def calculator(expression: str):
    """Evaluate arithmetic safely: + - * / // % ** and parentheses only."""
    return _safe_eval(ast.parse(str(expression), mode="eval"))


def wiki_search(query: str, k: int = 3) -> list[dict]:
    """Search the live knowledge graph; returns [{title, snippet}]."""
    try:
        from studio.data import wiki_pages
        pages = wiki_pages()
    except Exception:
        pages = []
    qs = {w for w in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(w) > 2}
    scored = []
    for p in pages:
        hay = (p.get("title", "") + " " + (p.get("body", "") or "")).lower()
        s = sum(hay.count(w) for w in qs)
        if s:
            scored.append((s, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"title": p.get("title"), "snippet": (p.get("body", "") or "").strip()[:200]}
            for _, p in scored[:max(1, int(k))]]


def datetime_now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def http_get(url: str, max_chars: int = 2000) -> dict:
    """SSRF-guarded HTTP GET. Returns {status, text} or {error}. Needs httpx."""
    from agents.net import safe_url
    if not safe_url(url):
        return {"error": "blocked url (ssrf guard): must be public http(s)"}
    try:
        import httpx
        r = httpx.get(url, timeout=10, follow_redirects=True)
        return {"status": r.status_code, "text": r.text[:int(max_chars)]}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def register_builtins(reg: ToolRegistry) -> ToolRegistry:
    reg.register(Tool("calculator", "Evaluate an arithmetic expression safely.",
                      calculator, {"expression": "string, e.g. '2*(3+4)'"}))
    reg.register(Tool("wiki_search", "Search the m1frame knowledge graph.",
                      wiki_search, {"query": "string", "k": "int (optional)"}))
    reg.register(Tool("datetime_now", "Current server date and time.", datetime_now, {}))
    reg.register(Tool("word_count", "Count words in text.", word_count, {"text": "string"}))
    reg.register(Tool("http_get", "Fetch a public URL (SSRF-guarded).",
                      http_get, {"url": "string", "max_chars": "int (optional)"}))
    return reg


_DEFAULT: ToolRegistry | None = None


def default_registry() -> ToolRegistry:
    """Process-wide registry pre-loaded with the built-ins."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = register_builtins(ToolRegistry())
    return _DEFAULT
