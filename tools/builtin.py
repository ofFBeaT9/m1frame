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
import base64 as _b64
import hashlib
import json as _json
import operator
import re
import time
import uuid as _uuid
from pathlib import Path as _Path
from urllib.parse import urlparse as _urlparse

from .registry import Tool, ToolRegistry

_ROOT = _Path(__file__).resolve().parent.parent  # tools are sandboxed to the workspace

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


# ── filesystem (sandboxed to the workspace root) ──────────────────────────────
def _safe_path(path: str) -> _Path:
    p = (_ROOT / str(path)).resolve()
    if p != _ROOT and _ROOT not in p.parents:
        raise ValueError("path escapes the m1frame workspace")
    return p


def read_file(path: str, max_chars: int = 4000) -> str:
    p = _safe_path(path)
    if not p.is_file():
        return f"(not a file: {path})"
    return p.read_text(encoding="utf-8", errors="replace")[:int(max_chars)]


def write_file(path: str, content: str) -> dict:   # DANGEROUS — requires approval
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(content), encoding="utf-8")
    return {"written": str(p.relative_to(_ROOT)).replace("\\", "/"), "bytes": len(str(content))}


def list_dir(path: str = ".") -> list:
    p = _safe_path(path)
    if not p.is_dir():
        return []
    return sorted(e.name + ("/" if e.is_dir() else "") for e in p.iterdir())[:200]


# ── data / encoding / misc ────────────────────────────────────────────────────
def json_query(data, path: str = ""):
    """Get a dotted path (a.b.0.c) from a JSON string or object."""
    if isinstance(data, str):
        try:
            data = _json.loads(data)
        except Exception:
            return None
    cur = data
    for part in [x for x in str(path).split(".") if x]:
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except Exception:
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def regex_extract(pattern: str, text: str, limit: int = 20) -> list:
    try:
        return re.findall(pattern, text or "")[:int(limit)]
    except re.error as e:
        return [f"(regex error: {e})"]


def base64_encode(text: str) -> str:
    return _b64.b64encode(str(text).encode("utf-8")).decode("ascii")


def base64_decode(text: str) -> str:
    try:
        return _b64.b64decode(str(text).encode("ascii")).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return f"(decode error: {e})"


def sha256(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def uuid4() -> str:
    return str(_uuid.uuid4())


def url_parse(url: str) -> dict:
    u = _urlparse(str(url))
    return {"scheme": u.scheme, "host": u.hostname, "port": u.port,
            "path": u.path, "query": u.query}


def convert_temp(value: float, to: str = "F") -> float:
    v = float(value)
    return round(v * 9 / 5 + 32, 2) if str(to).upper() == "F" else round((v - 32) * 5 / 9, 2)


def register_builtins(reg: ToolRegistry) -> ToolRegistry:
    reg.register(Tool("calculator", "Evaluate an arithmetic expression safely.",
                      calculator, {"expression": "string, e.g. '2*(3+4)'"}))
    reg.register(Tool("wiki_search", "Search the m1frame knowledge graph.",
                      wiki_search, {"query": "string", "k": "int (optional)"}))
    reg.register(Tool("datetime_now", "Current server date and time.", datetime_now, {}))
    reg.register(Tool("word_count", "Count words in text.", word_count, {"text": "string"}))
    reg.register(Tool("http_get", "Fetch a public URL (SSRF-guarded).",
                      http_get, {"url": "string", "max_chars": "int (optional)"}))
    reg.register(Tool("read_file", "Read a text file inside the workspace.",
                      read_file, {"path": "string"}))
    reg.register(Tool("write_file", "Write a text file inside the workspace.",
                      write_file, {"path": "string", "content": "string"}, dangerous=True))
    reg.register(Tool("list_dir", "List a directory inside the workspace.",
                      list_dir, {"path": "string (optional)"}))
    reg.register(Tool("json_query", "Get a dotted path (a.b.0) from JSON.",
                      json_query, {"data": "json|object", "path": "string"}))
    reg.register(Tool("regex_extract", "Find all regex matches in text.",
                      regex_extract, {"pattern": "regex", "text": "string"}))
    reg.register(Tool("base64_encode", "Base64-encode text.", base64_encode, {"text": "string"}))
    reg.register(Tool("base64_decode", "Base64-decode text.", base64_decode, {"text": "string"}))
    reg.register(Tool("sha256", "SHA-256 hex digest of text.", sha256, {"text": "string"}))
    reg.register(Tool("uuid4", "Generate a random UUID v4.", uuid4, {}))
    reg.register(Tool("url_parse", "Parse a URL into parts.", url_parse, {"url": "string"}))
    reg.register(Tool("convert_temp", "Convert temperature (C↔F).",
                      convert_temp, {"value": "number", "to": "F|C"}))
    return reg


_DEFAULT: ToolRegistry | None = None


def default_registry() -> ToolRegistry:
    """Process-wide registry pre-loaded with the built-ins."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = register_builtins(ToolRegistry())
    return _DEFAULT
