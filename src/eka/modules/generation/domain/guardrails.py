"""Prompt-injection guardrail.

Retrieved passages are untrusted: a document can contain text that tries to
hijack the model ("ignore previous instructions", etc.). This guard redacts
known override phrasings and reports whether anything was flagged. It is one
layer; the system prompt delimiting context as data is the other.
"""
from __future__ import annotations

import re

_PATTERNS = [
    re.compile(
        r"ignore\s+(?:all\s+|the\s+)?(?:previous|prior|above|earlier)\s+instructions?",
        re.IGNORECASE,
    ),
    re.compile(
        r"disregard\s+(?:all\s+|the\s+)?(?:previous|prior|above|earlier)\s+"
        r"(?:instructions?|context|text)",
        re.IGNORECASE,
    ),
    re.compile(r"forget\s+(?:everything|all\s+(?:previous|prior))", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
]

_REDACTION = "[redacted]"


class PromptInjectionGuard:
    def scan(self, text: str) -> tuple[str, bool]:
        flagged = False
        cleaned = text
        for pattern in _PATTERNS:
            cleaned, count = pattern.subn(_REDACTION, cleaned)
            if count:
                flagged = True
        return cleaned, flagged
