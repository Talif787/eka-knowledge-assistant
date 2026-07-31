"""JWT token issuer and verifier (PyJWT).

Uses HS256 with a shared secret, which is adequate for development. The ports let
a production deployment swap in RS256 with a JWKS endpoint from a real identity
provider without touching callers. Any decode failure (bad signature, expiry,
missing claim) surfaces as AuthenticationError, which the API maps to 401.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from eka.modules.identity.domain.identity import AuthenticatedIdentity
from eka.shared.domain.errors import AuthenticationError

_REQUIRED_CLAIMS = ["exp", "sub", "tid"]


class JwtTokenVerifier:
    def __init__(self, *, secret: str, algorithm: str, issuer: str) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._issuer = issuer

    def verify(self, token: str) -> AuthenticatedIdentity:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                options={"require": _REQUIRED_CLAIMS},
            )
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("invalid or expired token") from exc

        try:
            tenant_id = uuid.UUID(str(payload["tid"]))
        except (KeyError, ValueError) as exc:
            raise AuthenticationError("token has no valid tenant claim") from exc

        roles = frozenset(str(r) for r in payload.get("roles", []))
        return AuthenticatedIdentity(
            tenant_id=tenant_id, subject=str(payload["sub"]), roles=roles
        )


class JwtTokenIssuer:
    def __init__(self, *, secret: str, algorithm: str, issuer: str) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._issuer = issuer

    def issue(
        self,
        tenant_id: uuid.UUID,
        subject: str,
        roles: frozenset[str],
        ttl_seconds: int,
    ) -> str:
        now = datetime.now(UTC)
        claims: dict[str, Any] = {
            "iss": self._issuer,
            "sub": subject,
            "tid": str(tenant_id),
            "roles": sorted(roles),
            "iat": now,
            "exp": now + timedelta(seconds=ttl_seconds),
        }
        return jwt.encode(claims, self._secret, algorithm=self._algorithm)
