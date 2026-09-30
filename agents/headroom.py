"""Explicit request budgets; never guess a provider's model context window."""
from __future__ import annotations


def check_headroom(cfg: dict, backend: str, prompt: str, system: str = "",
                   history: list[dict] | None = None, max_tokens: int | None = None,
                   model: str | None = None) -> dict:
    policy = cfg.get("context") or {}
    bcfg = cfg.get(backend) or {}
    parts = [system, prompt] + [str(m.get("content", "")) for m in (history or [])]
    chars = sum(map(len, parts))
    cap = int(policy.get("max_input_chars", 120000))
    if cap <= 0 or chars > cap:
        raise ValueError(f"Context budget exceeded: {chars} input characters; limit {cap}. "
                         "Reduce selected skills/history or increase context.max_input_chars.")
    reserve = int(max_tokens if max_tokens is not None else bcfg.get("max_tokens", 4096))
    margin = int(policy.get("safety_margin_tokens", 1024))
    # UTF-8 bytes provide a deliberately conservative text-token estimate, not
    # a model-specific tokenizer. Provider framing is covered by the margin.
    estimate = sum(len(p.encode("utf-8")) for p in parts) + 16 * len(parts)
    configured_model = model or bcfg.get("model")
    windows = policy.get("model_windows") or {}
    window = windows.get(configured_model)
    if window is None and (model is None or model == bcfg.get("model")):
        window = bcfg.get("context_window_tokens")
    if reserve <= 0 or margin < 0:
        raise ValueError("Output reserve must be positive and context safety margin nonnegative")
    remaining = int(window) - estimate - reserve - margin if window is not None else None
    if remaining is not None and remaining < 0:
        raise ValueError("Insufficient configured context headroom for input plus output reserve. "
                         "Reduce context/output budgets or configure the correct model window.")
    return {"input_chars": chars, "input_limit_chars": cap,
            "estimated_input_tokens_upper": estimate, "output_reserve_tokens": reserve,
            "context_window_tokens": window, "remaining_tokens_lower": remaining,
            "estimate_method": "utf8_bytes_plus_framing", "external_headroom": False}
