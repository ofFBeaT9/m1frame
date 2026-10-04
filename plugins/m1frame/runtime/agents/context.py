"""Deterministic, bounded context packing without additional model calls."""
from __future__ import annotations


def clip(text: str, budget: int) -> str:
    """Keep both ends and explicitly mark omitted material."""
    if budget <= 0:
        return ""
    if len(text) <= budget:
        return text
    marker = "\n[... context omitted ...]\n"
    if budget <= len(marker):
        return marker[:budget]
    available = budget - len(marker)
    head = (available + 1) // 2
    tail = available - head
    return text[:head] + marker + (text[-tail:] if tail else "")


def pack_sections(sections: list[tuple[str, str]], budget: int) -> str:
    """Share space fairly so a long early output cannot erase later work."""
    if not sections or budget <= 0:
        return ""
    headers = [f"## {label}\n" for label, _ in sections]
    remaining = budget - sum(map(len, headers)) - 2 * (len(sections) - 1)
    if remaining < 0:
        return clip("\n\n".join(headers), budget)
    sizes = [0] * len(sections)
    pending = list(range(len(sections)))
    while pending:
        share = remaining // len(pending)
        small = [i for i in pending if len(sections[i][1]) <= share]
        if not small:
            for pos, i in enumerate(pending):
                sizes[i] = share + (pos < remaining % len(pending))
            break
        for i in small:
            sizes[i] = len(sections[i][1])
            remaining -= sizes[i]
            pending.remove(i)
    return "\n\n".join(h + clip(text, size)
                       for h, (_, text), size in zip(headers, sections, sizes, strict=False))


def chat_input(message: str, messages: list[dict], budget: int = 24000) -> tuple[str, list[dict]]:
    """Accept explicit message + prior history, or a full conversation list.

    Client-supplied system/tool roles are never promoted to trusted context.
    Keep only complete recent messages within the history character budget.
    """
    clean = [{"role": m["role"], "content": m["content"]} for m in messages
             if m.get("role") in ("user", "assistant")
             and isinstance(m.get("content"), str) and m["content"].strip()]
    if not message and clean and clean[-1]["role"] == "user":
        message = clean.pop()["content"]
    elif clean and clean[-1] == {"role": "user", "content": message}:
        clean.pop()
    history: list[dict] = []
    for item in reversed(clean):
        if len(item["content"]) > budget:
            break
        history.append(item)
        budget -= len(item["content"])
    history.reverse()
    while history and history[0]["role"] != "user":
        history.pop(0)
    return message, history
