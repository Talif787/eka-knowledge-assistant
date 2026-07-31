"""Unit tests for JWT issue/verify. Requires PyJWT (installed in CI)."""
from __future__ import annotations

import uuid

import pytest

from eka.modules.identity.infrastructure.jwt import JwtTokenIssuer, JwtTokenVerifier
from eka.shared.domain.errors import AuthenticationError

_SECRET = "unit-test-secret-at-least-32-bytes-long"
_ALG = "HS256"
_ISS = "eka-test"


def _pair(
    secret: str = _SECRET, issuer: str = _ISS
) -> tuple[JwtTokenIssuer, JwtTokenVerifier]:
    return (
        JwtTokenIssuer(secret=secret, algorithm=_ALG, issuer=issuer),
        JwtTokenVerifier(secret=secret, algorithm=_ALG, issuer=issuer),
    )


def test_round_trip_preserves_identity() -> None:
    issuer, verifier = _pair()
    tenant_id = uuid.uuid4()
    token = issuer.issue(tenant_id, "alice", frozenset({"admin"}), 3600)
    identity = verifier.verify(token)
    assert identity.tenant_id == tenant_id
    assert identity.subject == "alice"
    assert identity.has_role("admin")


def test_expired_token_rejected() -> None:
    issuer, verifier = _pair()
    token = issuer.issue(uuid.uuid4(), "u", frozenset(), -10)
    with pytest.raises(AuthenticationError):
        verifier.verify(token)


def test_wrong_secret_rejected() -> None:
    issuer, _ = _pair()
    token = issuer.issue(uuid.uuid4(), "u", frozenset(), 3600)
    _, verifier = _pair(secret="a-different-secret-also-32-bytes-long-xx")
    with pytest.raises(AuthenticationError):
        verifier.verify(token)


def test_wrong_issuer_rejected() -> None:
    issuer, _ = _pair(issuer="attacker")
    token = issuer.issue(uuid.uuid4(), "u", frozenset(), 3600)
    _, verifier = _pair(issuer="eka-test")
    with pytest.raises(AuthenticationError):
        verifier.verify(token)


def test_garbage_token_rejected() -> None:
    _, verifier = _pair()
    with pytest.raises(AuthenticationError):
        verifier.verify("not-a-jwt")
