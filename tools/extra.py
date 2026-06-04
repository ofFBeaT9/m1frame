"""
tools/extra.py — the rest of the auditable toolbelt.

These bring m1frame to 40+ built-in tools, but every one is small, pure, offline,
and readable — breadth without a black box. Registered into the default registry
by tools.builtin.register_builtins(). File tools reuse the workspace sandbox in
tools.builtin (_safe_path), so nothing here can read or write outside the repo.
"""
from __future__ import annotations

import binascii
import csv as _csv
import datetime as _dt
import difflib
import hashlib
import io
import re
import secrets
import statistics
from urllib.parse import quote, unquote

from .registry import Tool, ToolRegistry

_URL_RE = re.compile(r"https?://[^\s)>\]\"']+")


# ── encoding / hashing ────────────────────────────────────────────────────────
def md5(text: str) -> str:
    return hashlib.md5(str(text).encode("utf-8")).hexdigest()


def hex_encode(text: str) -> str:
    return binascii.hexlify(str(text).encode("utf-8")).decode("ascii")


def hex_decode(hexstr: str) -> str:
    try:
        return binascii.unhexlify(str(hexstr).strip()).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return f"(hex error: {e})"


def url_encode(text: str) -> str:
    return quote(str(text), safe="")


def url_decode(text: str) -> str:
    return unquote(str(text))


def random_string(length: int = 16) -> str:
    return secrets.token_hex(max(1, int(length)))[: int(length)]


def base_convert(value: str, from_base: int = 10, to_base: int = 16) -> str:
    n = int(str(value), int(from_base))
    if int(to_base) == 10:
        return str(n)
    digits, neg = "0123456789abcdefghijklmnopqrstuvwxyz", n < 0
    n = abs(n)
    out = ""
    while n:
        out = digits[n % int(to_base)] + out
        n //= int(to_base)
    return ("-" if neg else "") + (out or "0")


# ── text ──────────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(text).lower())).strip("-")


def title_case(text: str) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in str(text).split())


def sort_lines(text: str, reverse: bool = False) -> str:
    return "\n".join(sorted(str(text).splitlines(), reverse=bool(reverse)))


def dedupe_lines(text: str) -> str:
    seen, out = set(), []
    for ln in str(text).splitlines():
        if ln not in seen:
            seen.add(ln)
            out.append(ln)
    return "\n".join(out)


def diff_text(a: str, b: str) -> str:
    return "\n".join(difflib.unified_diff(str(a).splitlines(), str(b).splitlines(),
                                          "a", "b", lineterm=""))


def template_render(template: str, values: dict | None = None) -> str:
    out = str(template)
    for k, v in (values or {}).items():
        out = out.replace("{{" + str(k) + "}}", str(v))
    return out


def markdown_to_text(md: str) -> str:
    t = str(md)
    t = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", t)
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[#>*_~|-]", " ", t)
    return re.sub(r"[ \t]{2,}", " ", t).strip()


def extract_urls(text: str, limit: int = 50) -> list:
    return _URL_RE.findall(str(text))[: int(limit)]


# ── data ──────────────────────────────────────────────────────────────────────
def json_format(data, indent: int = 2) -> str:
    import json as _json
    if isinstance(data, str):
        data = _json.loads(data)
    return _json.dumps(data, indent=int(indent), ensure_ascii=False, sort_keys=False)


def csv_to_json(text: str) -> list:
    return list(_csv.DictReader(io.StringIO(str(text))))


def yaml_to_json(text: str):
    try:
        import yaml
    except Exception:
        return {"error": "pyyaml not installed"}
    return yaml.safe_load(str(text))


def stats_summary(numbers: list) -> dict:
    xs = [float(x) for x in (numbers or [])]
    if not xs:
        return {"count": 0}
    return {"count": len(xs), "sum": round(sum(xs), 6), "mean": round(statistics.fmean(xs), 6),
            "median": round(statistics.median(xs), 6), "min": min(xs), "max": max(xs),
            "stdev": round(statistics.pstdev(xs), 6)}


# ── time ──────────────────────────────────────────────────────────────────────
def timestamp() -> dict:
    now = _dt.datetime.now(_dt.timezone.utc)
    return {"iso": now.isoformat(), "epoch": int(now.timestamp())}


def time_delta(start: str, end: str) -> dict:
    def _p(s):
        return _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    secs = (_p(end) - _p(start)).total_seconds()
    return {"seconds": secs, "minutes": round(secs / 60, 3), "hours": round(secs / 3600, 4),
            "days": round(secs / 86400, 5)}


# ── files (sandboxed via tools.builtin._safe_path) ────────────────────────────
def file_stat(path: str) -> dict:
    from .builtin import _safe_path
    p = _safe_path(path)
    if not p.exists():
        return {"exists": False}
    st = p.stat()
    return {"exists": True, "is_dir": p.is_dir(), "bytes": st.st_size,
            "modified": _dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}


def head_file(path: str, lines: int = 20) -> str:
    from .builtin import _safe_path
    p = _safe_path(path)
    if not p.is_file():
        return f"(not a file: {path})"
    with p.open(encoding="utf-8", errors="replace") as fh:
        return "".join([next(fh, "") for _ in range(max(1, int(lines)))])


def grep_files(pattern: str, path: str = ".", glob: str = "*", limit: int = 50) -> list:
    from .builtin import _safe_path
    base = _safe_path(path)
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return [f"(regex error: {e})"]
    hits = []
    files = [base] if base.is_file() else sorted(base.rglob(glob))
    for f in files:
        if not f.is_file():
            continue
        try:
            for i, ln in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if rx.search(ln):
                    hits.append({"file": str(f).replace("\\", "/"), "line": i, "text": ln.strip()[:200]})
                    if len(hits) >= int(limit):
                        return hits
        except Exception:  # noqa: BLE001
            continue
    return hits


def register_extras(reg: ToolRegistry) -> ToolRegistry:
    specs = [
        ("md5", "MD5 hex digest of text.", md5, {"text": "string"}),
        ("hex_encode", "Hex-encode text.", hex_encode, {"text": "string"}),
        ("hex_decode", "Hex-decode to text.", hex_decode, {"hexstr": "string"}),
        ("url_encode", "Percent-encode a string.", url_encode, {"text": "string"}),
        ("url_decode", "Percent-decode a string.", url_decode, {"text": "string"}),
        ("random_string", "Random hex string of length N.", random_string, {"length": "int"}),
        ("base_convert", "Convert a number between bases.", base_convert,
         {"value": "string", "from_base": "int", "to_base": "int"}),
        ("slugify", "Make a URL-safe slug.", slugify, {"text": "string"}),
        ("title_case", "Title-case a string.", title_case, {"text": "string"}),
        ("sort_lines", "Sort lines of text.", sort_lines, {"text": "string", "reverse": "bool"}),
        ("dedupe_lines", "Remove duplicate lines.", dedupe_lines, {"text": "string"}),
        ("diff_text", "Unified diff of two texts.", diff_text, {"a": "string", "b": "string"}),
        ("template_render", "Render {{var}} placeholders.", template_render,
         {"template": "string", "values": "object"}),
        ("markdown_to_text", "Strip Markdown to plain text.", markdown_to_text, {"md": "string"}),
        ("extract_urls", "Extract URLs from text.", extract_urls, {"text": "string"}),
        ("json_format", "Pretty-print JSON.", json_format, {"data": "json|object", "indent": "int"}),
        ("csv_to_json", "Parse CSV into row objects.", csv_to_json, {"text": "csv string"}),
        ("yaml_to_json", "Parse YAML into an object.", yaml_to_json, {"text": "yaml string"}),
        ("stats_summary", "Summary stats of a number list.", stats_summary, {"numbers": "list"}),
        ("timestamp", "Current UTC time (iso + epoch).", timestamp, {}),
        ("time_delta", "Duration between two ISO times.", time_delta, {"start": "iso", "end": "iso"}),
        ("file_stat", "Stat a workspace file.", file_stat, {"path": "string"}),
        ("head_file", "First N lines of a workspace file.", head_file, {"path": "string", "lines": "int"}),
        ("grep_files", "Regex-search workspace files.", grep_files,
         {"pattern": "regex", "path": "string", "glob": "string"}),
    ]
    for name, desc, fn, schema in specs:
        reg.register(Tool(name, desc, fn, schema))
    return reg
