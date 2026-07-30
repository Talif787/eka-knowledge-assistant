"""Documents bounded context: the Document aggregate.

A Document is the unit of ingestion. It owns its lifecycle state machine and
guards the invariants that must hold regardless of how it is persisted or
exposed. No infrastructure concerns leak in here.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from eka.shared.domain.base import AggregateRoot, DomainEvent, new_uuid, utcnow
from eka.shared.domain.errors import StateTransitionError, ValidationError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_TITLE_LEN = 512


class SourceType(str, Enum):
    UPLOAD = "upload"
    CONFLUENCE = "confluence"
    SHAREPOINT = "sharepoint"
    JIRA = "jira"
    NOTION = "notion"
    GOOGLE_DRIVE = "google_drive"


class DocumentStatus(str, Enum):
    REGISTERED = "registered"
    INGESTING = "ingesting"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


_ALLOWED_TRANSITIONS: dict[DocumentStatus, frozenset[DocumentStatus]] = {
    DocumentStatus.REGISTERED: frozenset({DocumentStatus.INGESTING, DocumentStatus.DELETED}),
    DocumentStatus.INGESTING: frozenset(
        {DocumentStatus.INDEXED, DocumentStatus.FAILED, DocumentStatus.DELETED}
    ),
    DocumentStatus.INDEXED: frozenset({DocumentStatus.INGESTING, DocumentStatus.DELETED}),
    DocumentStatus.FAILED: frozenset({DocumentStatus.INGESTING, DocumentStatus.DELETED}),
    DocumentStatus.DELETED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class ContentHash:
    value: str

    def __post_init__(self) -> None:
        if not _SHA256_RE.match(self.value):
            raise ValidationError("content_hash must be a lowercase hex sha256 digest")


@dataclass(frozen=True, slots=True)
class Title:
    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise ValidationError("title must not be empty")
        if len(stripped) > _MAX_TITLE_LEN:
            raise ValidationError(f"title must be at most {_MAX_TITLE_LEN} characters")
        object.__setattr__(self, "value", stripped)


@dataclass(frozen=True, slots=True)
class DocumentRegistered(DomainEvent):
    document_id: uuid.UUID = None  # type: ignore[assignment]
    tenant_id: uuid.UUID = None  # type: ignore[assignment]
    collection_id: uuid.UUID = None  # type: ignore[assignment]
    content_hash: str = ""


@dataclass(frozen=True, slots=True)
class DocumentContentChanged(DomainEvent):
    document_id: uuid.UUID = None  # type: ignore[assignment]
    tenant_id: uuid.UUID = None  # type: ignore[assignment]
    new_content_hash: str = ""
    version: int = 0


@dataclass(frozen=True, slots=True)
class DocumentDeleted(DomainEvent):
    document_id: uuid.UUID = None  # type: ignore[assignment]
    tenant_id: uuid.UUID = None  # type: ignore[assignment]


class Document(AggregateRoot):
    def __init__(
        self,
        *,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        collection_id: uuid.UUID,
        title: Title,
        source_type: SourceType,
        source_uri: str,
        content_hash: ContentHash,
        status: DocumentStatus,
        version: int,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        super().__init__()
        self.id = id
        self.tenant_id = tenant_id
        self.collection_id = collection_id
        self.title = title
        self.source_type = source_type
        self.source_uri = source_uri
        self.content_hash = content_hash
        self.status = status
        self.version = version
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def register(
        cls,
        *,
        tenant_id: uuid.UUID,
        collection_id: uuid.UUID,
        title: Title,
        source_type: SourceType,
        source_uri: str,
        content_hash: ContentHash,
    ) -> "Document":
        now = utcnow()
        doc = cls(
            id=new_uuid(),
            tenant_id=tenant_id,
            collection_id=collection_id,
            title=title,
            source_type=source_type,
            source_uri=source_uri,
            content_hash=content_hash,
            status=DocumentStatus.REGISTERED,
            version=1,
            created_at=now,
            updated_at=now,
        )
        doc.record(
            DocumentRegistered(
                document_id=doc.id,
                tenant_id=tenant_id,
                collection_id=collection_id,
                content_hash=content_hash.value,
            )
        )
        return doc

    def _transition(self, target: DocumentStatus) -> None:
        if target not in _ALLOWED_TRANSITIONS[self.status]:
            raise StateTransitionError(
                f"cannot move document from {self.status.value} to {target.value}"
            )
        self.status = target
        self.updated_at = utcnow()

    def mark_ingesting(self) -> None:
        self._transition(DocumentStatus.INGESTING)

    def mark_indexed(self) -> None:
        self._transition(DocumentStatus.INDEXED)

    def mark_failed(self) -> None:
        self._transition(DocumentStatus.FAILED)

    def change_content(self, new_hash: ContentHash) -> None:
        if self.status is DocumentStatus.DELETED:
            raise StateTransitionError("cannot change content of a deleted document")
        if new_hash.value == self.content_hash.value:
            return
        self.content_hash = new_hash
        self.version += 1
        self.status = DocumentStatus.REGISTERED
        self.updated_at = utcnow()
        self.record(
            DocumentContentChanged(
                document_id=self.id,
                tenant_id=self.tenant_id,
                new_content_hash=new_hash.value,
                version=self.version,
            )
        )

    def delete(self) -> None:
        if self.status is DocumentStatus.DELETED:
            return
        self._transition(DocumentStatus.DELETED)
        self.record(DocumentDeleted(document_id=self.id, tenant_id=self.tenant_id))
