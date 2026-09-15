"""ADHD-friendly output shaping inspired by ayghri/i-have-adhd.

The upstream project is a prompt skill, not a Python runtime dependency. This
module keeps its actionable rules available to m1frame without requiring a
plugin installation. Formatting is intentionally conservative so structured
agent output remains byte-for-byte safe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SOURCE = "https://github.com/ayghri/i-have-adhd"

ADHD_SYSTEM_GUIDANCE = (
    "Shape the response for actionability: lead with the next action; number "
    "multi-step tasks; suppress tangents; use matter-of-fact errors; keep lists "
    "short; end with one concrete next step. Do not add a preamble or closing "
    "pleasantry."
)

_PREAMBLE = re.compile(
    r"^(?:great question[!.]?\s*|sure[!.]?\s*|let me (?:think|help)[^.\n]*[.!]\s*)",
    re.IGNORECASE,
)
_CLOSER = re.compile(
    r"(?:\n+)?(?:hope this helps[!.]?|let me know if you need anything else[!.]?|"
    r"feel free to ask[!.]?)\s*$",
    re.IGNORECASE,
)


def _is_structured(text: str) -> bool:
    stripped = text.lstrip()
    return (
        stripped.startswith(("```", "{", "[", "---"))
        or (stripped.startswith("<") and "</" in stripped)
    )


@dataclass(frozen=True)
class ADHDFormatter:
    """Conservative formatter for final prose only."""

    enabled: bool = False

    def format(self, text: str) -> str:
        if not self.enabled or not text or _is_structured(text):
            return text
        result = _PREAMBLE.sub("", text.strip(), count=1)
        result = _CLOSER.sub("", result).rstrip()
        return result

    def system_guidance(self, system: str = "") -> str:
        if not self.enabled:
            return system
        return f"{system}\n\n{ADHD_SYSTEM_GUIDANCE}" if system else ADHD_SYSTEM_GUIDANCE

    def status(self) -> dict:
        return {"enabled": self.enabled, "available": True, "source": SOURCE}
