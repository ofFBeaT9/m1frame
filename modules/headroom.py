"""Optional adapter for headroom-ai context compression.

Headroom is deliberately not a required m1frame dependency. The adapter
returns the original messages for missing packages, unsupported versions, and
runtime failures, while preserving diagnostics for observability.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SOURCE = "https://github.com/headroomlabs-ai/headroom"


@dataclass(frozen=True)
class CompressionResult:
    messages: list[dict[str, Any]]
    available: bool
    applied: bool = False
    tokens_before: int = 0
    tokens_after: int = 0
    tokens_saved: int = 0
    compression_ratio: float = 0.0
    transforms_applied: list[str] = field(default_factory=list)
    error: str | None = None

    def status(self) -> dict:
        return {
            "enabled": True,
            "available": self.available,
            "applied": self.applied,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "tokens_saved": self.tokens_saved,
            "compression_ratio": self.compression_ratio,
            "transforms_applied": list(self.transforms_applied),
            "error": self.error,
            "source": SOURCE,
        }


class HeadroomAdapter:
    """Lazy, opt-in Headroom integration with a safe passthrough fallback."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.enabled = bool(self.config.get("enabled", False))
        self._compress = None
        self._import_error: str | None = None
        if self.enabled:
            try:
                from headroom import compress
                self._compress = compress
            except (ImportError, AttributeError) as exc:
                self._import_error = str(exc)

    def compress_messages(self, messages: list[dict[str, Any]], model: str = "") -> CompressionResult:
        original = list(messages)
        if not self.enabled:
            return CompressionResult(messages=original, available=False)
        if self._compress is None:
            return CompressionResult(
                messages=original, available=False, error=self._import_error or "headroom unavailable"
            )
        kwargs = {
            key: self.config[key]
            for key in ("model_limit", "target_ratio", "protect_recent", "min_tokens_to_compress")
            if key in self.config and self.config[key] is not None
        }
        try:
            result = self._compress(
                original,
                model=model or self.config.get("model") or "claude-sonnet-4-5-20250929",
                **kwargs,
            )
            compressed = list(getattr(result, "messages", original))
            if not self._valid_messages(compressed):
                return CompressionResult(
                    messages=original,
                    available=True,
                    error="headroom returned an invalid message payload",
                )
            before = int(getattr(result, "tokens_before", 0) or 0)
            after = int(getattr(result, "tokens_after", 0) or 0)
            return CompressionResult(
                messages=compressed,
                available=True,
                applied=compressed != original,
                tokens_before=before,
                tokens_after=after,
                tokens_saved=int(getattr(result, "tokens_saved", max(0, before - after)) or 0),
                compression_ratio=float(getattr(result, "compression_ratio", 0.0) or 0.0),
                transforms_applied=list(getattr(result, "transforms_applied", []) or []),
            )
        except Exception as exc:  # noqa: BLE001 - optional adapter must preserve the request
            return CompressionResult(messages=original, available=True, error=str(exc))

    @staticmethod
    def _valid_messages(messages: list[dict[str, Any]]) -> bool:
        return bool(messages) and all(
            isinstance(message, dict)
            and isinstance(message.get("role"), str)
            and "content" in message
            for message in messages
        )

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "available": self._compress is not None,
            "error": self._import_error,
            "source": SOURCE,
        }
