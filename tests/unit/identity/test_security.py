"""Unit tests for the auth dependency. Requires PyJWT and FastAPI (CI)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from eka.api.security import get_current_identity
from eka.modules.identity.infrastructure.jwt import JwtTokenIssuer, JwtTokenVerifier
from eka.shared.domain.errors import AuthenticationError

_SECRET = "security-test-secret-at-least-32-bytes-x"
_ALG = "HS256"
_ISS = "eka"


def _verifier() -> JwtTokenVerifier:
    return JwtTokenVerifier(secret=_SECRET, algorithm=_ALG, issuer=_ISS)


def test_missing_credentials_rejected() -> None:
    with pytest.raises(AuthenticationError):
        get_current_identity(credentials=None, verifier=_verifier())


def test_valid_token_returns_identity() -> None:
    issuer = JwtTokenIssuer(secret=_SECRET, algorithm=_ALG, issuer=_ISS)
    tenant_id = uuid.uuid4()
    token = issuer.issue(tenant_id, "bob", frozenset(), 3600)
    credentials = SimpleNamespace(scheme="Bearer", credentials=token)
    identity = get_current_identity(credentials=credentials, verifier=_verifier())
    assert identity.tenant_id == tenant_id
    assert identity.subject == "bob"


def test_invalid_token_rejected() -> None:
    credentials = SimpleNamespace(scheme="Bearer", credentials="garbage")
    with pytest.raises(AuthenticationError):
        get_current_identity(credentials=credentials, verifier=_verifier())
