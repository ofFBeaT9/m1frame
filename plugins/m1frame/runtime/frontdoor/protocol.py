"""Model-agnostic tool-call parsing.

The original tool loop only recognised a reply that was *exactly* a JSON object.
Claude follows that reliably; most other models (GPT, Gemini, Llama, Qwen, Gemma)
wrap the JSON in ```json fences or add a sentence before it, so the call was
silently treated as the final answer and no tool ever ran. This parser finds the
first balanced JSON object carrying the tool key anywhere in the reply.
"""
from __future__ import annotations

import json
import re

TOOL_KEYS = ("m1frame_tool", "tool", "name")
_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)


def _balanced_objects(text: str):
    """Yield every top-level {...} substring, respecting strings and escapes."""
    depth, start, in_str, esc = 0, None, False, False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start:i + 1]
                start = None


def parse_tool_call(raw: str, known: set[str] | None = None) -> tuple[str, dict] | None:
    """Return (tool_name, arguments) if the reply requests a tool, else None.

    Accepts {"m1frame_tool": ..., "arguments": {...}} (the m1frame contract) and the
    common shapes other models drift to: {"tool": ...}, {"name": ..., "arguments"|"args"
    |"parameters": ...}. Bare {"name": ...} only counts when the name is a known tool,
    so ordinary JSON deliverables are not mistaken for calls.
    """
    if not isinstance(raw, str) or "{" not in raw:
        return None
    candidates = [m.group(1) for m in _FENCE.finditer(raw)] + [raw]
    for chunk in candidates:
        for blob in _balanced_objects(chunk):
            try:
                obj = json.loads(blob, strict=False)
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue
            for key in TOOL_KEYS:
                name = obj.get(key)
                if not isinstance(name, str):
                    continue
                if key == "name" and (known is None or name not in known):
                    continue
                if key == "tool" and known is not None and name not in known:
                    continue
                args = obj.get("arguments", obj.get("args", obj.get("parameters", {})))
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                return name, args if isinstance(args, dict) else {}
    return None
