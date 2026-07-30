"""Recursive character chunker.

Splits text on progressively finer separators (paragraph, line, sentence, word)
so chunks respect natural boundaries where possible, then packs pieces up to a
target size with a fixed overlap to preserve context across chunk edges.

Strategy pattern: alternative chunkers (semantic, layout-aware) can implement the
Chunker port without touching the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass

from eka.modules.ingestion.domain.chunk import TextPiece
from eka.shared.domain.errors import ValidationError

_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    chunk_size: int = 800
    chunk_overlap: int = 120

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValidationError("chunk_size must be positive")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValidationError("chunk_overlap must be in [0, chunk_size)")


class RecursiveCharacterChunker:
    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self._config = config or ChunkingConfig()

    def split(self, text: str) -> list[TextPiece]:
        normalized = text.strip()
        if not normalized:
            return []
        fragments = self._recursive_split(normalized, 0)
        merged = self._merge_with_overlap(fragments)
        return [TextPiece(ordinal=i, text=t) for i, t in enumerate(merged)]

    def _recursive_split(self, text: str, sep_index: int) -> list[str]:
        if len(text) <= self._config.chunk_size or sep_index >= len(_SEPARATORS):
            return [text]
        separator = _SEPARATORS[sep_index]
        parts = list(text) if separator == "" else text.split(separator)
        result: list[str] = []
        for part in parts:
            piece = part if separator == "" else part + separator
            piece = piece.rstrip() if separator in ("\n\n", "\n") else piece
            if not piece:
                continue
            if len(piece) > self._config.chunk_size:
                result.extend(self._recursive_split(piece, sep_index + 1))
            else:
                result.append(piece)
        return result

    def _merge_with_overlap(self, fragments: list[str]) -> list[str]:
        chunks: list[str] = []
        current = ""
        for fragment in fragments:
            candidate = f"{current} {fragment}".strip() if current else fragment
            if len(candidate) <= self._config.chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current)
                current = (self._tail(current) + " " + fragment).strip()
            else:
                chunks.append(fragment[: self._config.chunk_size])
                current = fragment[self._config.chunk_size - self._config.chunk_overlap :]
        if current:
            chunks.append(current)
        return chunks

    def _tail(self, text: str) -> str:
        if self._config.chunk_overlap == 0:
            return ""
        return text[-self._config.chunk_overlap :]
