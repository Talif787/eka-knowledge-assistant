"""Unit tests for the Document aggregate.

Pure-domain tests: no database, no framework, no I/O. They assert invariants and
state-machine behavior and run in milliseconds.
"""

from __future__ import annotations

import uuid

import pytest

from eka.modules.documents.domain.document import (
    ContentHash,
    Document,
    DocumentContentChanged,
    DocumentDeleted,
    DocumentRegistered,
    DocumentStatus,
    SourceType,
    Title,
)
from eka.shared.domain.errors import StateTransitionError, ValidationError

VALID_HASH = "a" * 64
OTHER_HASH = "b" * 64


def _register() -> Document:
    return Document.register(
        tenant_id=uuid.uuid4(),
        collection_id=uuid.uuid4(),
        title=Title("Onboarding Guide"),
        source_type=SourceType.UPLOAD,
        source_uri="s3://bucket/key",
        content_hash=ContentHash(VALID_HASH),
    )


def test_title_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        Title("   ")


def test_title_trims_whitespace() -> None:
    assert Title("  Guide  ").value == "Guide"


def test_content_hash_rejects_non_sha256() -> None:
    with pytest.raises(ValidationError):
        ContentHash("not-a-hash")


def test_register_starts_registered_and_emits_event() -> None:
    doc = _register()
    assert doc.status is DocumentStatus.REGISTERED
    assert doc.version == 1
    events = doc.pull_events()
    assert len(events) == 1 and isinstance(events[0], DocumentRegistered)
    assert doc.pull_events() == []  # events drained


def test_happy_path_lifecycle() -> None:
    doc = _register()
    doc.mark_ingesting()
    doc.mark_indexed()
    assert doc.status is DocumentStatus.INDEXED


def test_illegal_transition_raises() -> None:
    doc = _register()
    with pytest.raises(StateTransitionError):
        doc.mark_indexed()  # cannot go registered -> indexed directly


def test_change_content_bumps_version_and_resets_status() -> None:
    doc = _register()
    doc.mark_ingesting()
    doc.mark_indexed()
    doc.change_content(ContentHash(OTHER_HASH))
    assert doc.version == 2
    assert doc.status is DocumentStatus.REGISTERED
    events = [e for e in doc.pull_events() if isinstance(e, DocumentContentChanged)]
    assert len(events) == 1 and events[0].version == 2


def test_change_content_is_noop_when_hash_unchanged() -> None:
    doc = _register()
    doc.pull_events()
    doc.change_content(ContentHash(VALID_HASH))
    assert doc.version == 1
    assert doc.pull_events() == []


def test_delete_emits_event_and_is_idempotent() -> None:
    doc = _register()
    doc.pull_events()
    doc.delete()
    doc.delete()  # second call is a no-op
    events = doc.pull_events()
    assert len(events) == 1 and isinstance(events[0], DocumentDeleted)
    assert doc.status is DocumentStatus.DELETED


def test_cannot_change_content_after_delete() -> None:
    doc = _register()
    doc.delete()
    with pytest.raises(StateTransitionError):
        doc.change_content(ContentHash(OTHER_HASH))
