"""Unit tests for the AuthenticatedIdentity value object (pure, offline)."""
from __future__ import annotations

import uuid

from eka.modules.identity.domain.identity import AuthenticatedIdentity


def test_has_role_true_and_false() -> None:
    identity = AuthenticatedIdentity(uuid.uuid4(), "user", frozenset({"admin"}))
    assert identity.has_role("admin")
    assert not identity.has_role("editor")


def test_no_roles_grants_nothing() -> None:
    identity = AuthenticatedIdentity(uuid.uuid4(), "user", frozenset())
    assert not identity.has_role("admin")
