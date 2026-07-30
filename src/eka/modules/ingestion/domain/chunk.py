"""The Chunk entity and the chunking port.

A Chunk is a retrievable unit of a document: its text, its position, and its
embedding, tagged with tenant and document so retrieval can enforce access and
attribution. Chunks are always produced and replaced as a set for a document.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from eka.modules.ingestion.domain.embedding import Embedding
from eka.shared.domain.base import Entity, new_uuid
from eka.shared.domain.errors import ValidationError


@dataclass(frozen=True, slots=True)
class ChunkText:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValidationError("chunk text must not be empty")


class Chunk(Entity):
    def __init__(
        self,
        *,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        collection_id: uuid.UUID,
        document_version: int,
        ordinal: int,
        text: ChunkText,
        embedding: Embedding,
    ) -> None:
        if ordinal < 0:
            raise ValidationError("ordinal must be non-negative")
        self.id = id
        self.tenant_id = tenant_id
        self.document_id = document_id
        self.collection_id = collection_id
        self.document_version = document_version
        self.ordinal = ordinal
        self.text = text
        self.embedding = embedding

    @classmethod
    def create(
        cls,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        collection_id: uuid.UUID,
        document_version: int,
        ordinal: int,
        text: str,
        embedding: Embedding,
    ) -> Chunk:
        return cls(
            id=new_uuid(),
            tenant_id=tenant_id,
            document_id=document_id,
            collection_id=collection_id,
            document_version=document_version,
            ordinal=ordinal,
            text=ChunkText(text),
            embedding=embedding,
        )


@dataclass(frozen=True, slots=True)
class TextPiece:
    """A pre-embedding fragment produced by the chunker."""

    ordinal: int
    text: str


@runtime_checkable
class Chunker(Protocol):
    def split(self, text: str) -> list[TextPiece]: ...
