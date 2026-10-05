"""Final-answer boundary shared by providers, workflows and UI delivery."""
from __future__ import annotations

import re


def clean_answer(text: str, thought_tag: str = 'thought') -> str:
    """Remove private reasoning blocks; unmatched openings fail closed.

    This deliberately handles complete text rather than exposing unvalidated
    partial chunks. A model's reasoning is never a required output artifact.
    """
    tags = '|'.join(re.escape(t) for t in {'thought', 'think', 'analysis', 'reasoning', thought_tag})
    token = re.compile(rf'<\s*(/?)\s*({tags})\b[^>]*>', re.I)
    depth, start, parts = 0, 0, []
    for match in token.finditer(text):
        closing = bool(match.group(1))
        if not closing:
            if depth == 0:
                parts.append(text[start:match.start()])
            depth += 1
        elif depth:
            depth -= 1
            if depth == 0:
                start = match.end()
        else:
            # An orphan close may follow reasoning emitted without its opener.
            parts = []
            start = match.end()
    if depth == 0:
        parts.append(text[start:])
    answer = ''.join(parts).strip()
    # Partial opening tags at the end are not a completed final answer.
    answer = re.sub(rf'<\s*(?:{tags})(?:\s[^>]*)?$', '', answer, flags=re.I).strip()
    return answer


def delivery_text(text: str) -> str:
    answer = clean_answer(text)
    if not answer:
        raise ValueError('No final answer remained after output validation')
    return answer
