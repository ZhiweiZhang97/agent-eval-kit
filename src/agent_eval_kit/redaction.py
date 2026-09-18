from __future__ import annotations

import re
from typing import Any

_SECRET_PATTERNS = [
    re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(
        r"(?i)(api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*"
        r"([A-Za-z0-9._~+/=-]{12,})"
    ),
]


def redact_text(value: str) -> str:
    redacted = value
    redacted = _SECRET_PATTERNS[0].sub("[REDACTED_TOKEN]", redacted)
    redacted = _SECRET_PATTERNS[1].sub("Bearer [REDACTED_TOKEN]", redacted)

    def replace_named(match: re.Match[str]) -> str:
        return f"{match.group(1)}=[REDACTED_TOKEN]"

    redacted = _SECRET_PATTERNS[2].sub(replace_named, redacted)
    return redacted


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    return value
