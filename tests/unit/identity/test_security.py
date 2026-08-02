"""Unit tests for the auth dependency. Requires PyJWT and FastAPI (CI)."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from eka.api.security import get_current_identity
from eka.modules.identity.infrastructure.jwt import JwtTokenIssuer, JwtTokenVerifier
from eka.shared.domain.errors import AuthenticationError

_SECRET = "test-secret-please-change-0123456789abcdef"
_ALG = "HS256"
_ISS = "eka"


def _verifier() -> JwtTokenVerifier:
    return JwtTokenVerifier(secret=_SECRET, algorithm=_ALG, issuer=_ISS)


def _request(headers: dict[str, str] | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "headers": raw})


def test_missing_credentials_rejected() -> None:
    with pytest.raises(AuthenticationError):
        get_current_identity(request=_request(), credentials=None, verifier=_verifier())


def test_valid_token_returns_identity() -> None:
    issuer = JwtTokenIssuer(secret=_SECRET, algorithm=_ALG, issuer=_ISS)
    tenant_id = uuid.uuid4()
    token = issuer.issue(tenant_id, "bob", frozenset(), 3600)
    credentials = SimpleNamespace(scheme="Bearer", credentials=token)
    identity = get_current_identity(
        request=_request(), credentials=credentials, verifier=_verifier()
    )
    assert identity.tenant_id == tenant_id
    assert identity.subject == "bob"


def test_invalid_token_rejected() -> None:
    credentials = SimpleNamespace(scheme="Bearer", credentials="garbage")
    with pytest.raises(AuthenticationError):
        get_current_identity(
            request=_request(), credentials=credentials, verifier=_verifier()
        )


def test_x_eka_token_header_accepted() -> None:
    issuer = JwtTokenIssuer(secret=_SECRET, algorithm=_ALG, issuer=_ISS)
    tenant_id = uuid.uuid4()
    token = issuer.issue(tenant_id, "carol", frozenset(), 3600)
    identity = get_current_identity(
        request=_request({"X-EKA-Token": token}), credentials=None, verifier=_verifier()
    )
    assert identity.tenant_id == tenant_id
    assert identity.subject == "carol"
