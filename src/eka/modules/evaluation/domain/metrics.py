"""Answer-quality metrics.

Deterministic, dependency-free lexical proxies for the LLM-judged RAGAS metrics.
They are not a substitute for a model-graded evaluation, but they are stable,
fast, and good enough to catch regressions in retrieval and grounding, which is
what a CI gate needs. A production setup would add model-graded scores on top.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "or",
        "but",
        "with",
        "as",
        "by",
        "at",
        "from",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "how",
        "what",
        "why",
        "when",
        "where",
        "which",
        "who",
        "do",
        "does",
        "did",
        "can",
        "could",
        "will",
        "would",
        "should",
        "so",
        "if",
        "then",
    }
)


def _content_tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def _keyword_tokens(keywords: list[str]) -> set[str]:
    tokens: set[str] = set()
    for keyword in keywords:
        tokens |= _content_tokens(keyword)
    return tokens


def context_recall(expected_keywords: list[str], contexts: list[str]) -> float:
    """Fraction of expected answer keywords present in the retrieved contexts."""
    expected = _keyword_tokens(expected_keywords)
    if not expected:
        return 1.0
    retrieved = set().union(*(_content_tokens(c) for c in contexts)) if contexts else set()
    return len(expected & retrieved) / len(expected)


def context_precision(question: str, contexts: list[str]) -> float:
    """Fraction of retrieved contexts that share content with the question."""
    if not contexts:
        return 0.0
    question_tokens = _content_tokens(question)
    if not question_tokens:
        return 0.0
    relevant = sum(1 for c in contexts if _content_tokens(c) & question_tokens)
    return relevant / len(contexts)


def faithfulness(answer: str, contexts: list[str]) -> float:
    """Fraction of the answer's content tokens supported by the contexts."""
    answer_tokens = _content_tokens(answer)
    if not answer_tokens:
        return 1.0
    supported = set().union(*(_content_tokens(c) for c in contexts)) if contexts else set()
    return len(answer_tokens & supported) / len(answer_tokens)


def answer_relevance(answer: str, expected_keywords: list[str]) -> float:
    """Fraction of expected keywords that appear in the answer."""
    expected = _keyword_tokens(expected_keywords)
    if not expected:
        return 1.0
    return len(expected & _content_tokens(answer)) / len(expected)
