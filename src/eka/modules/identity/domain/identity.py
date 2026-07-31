"""Identity value object and token ports.

An AuthenticatedIdentity is what the API trusts after a token is verified: the
tenant the caller belongs to, the subject (user), and their roles. The tenant is
proven by the token signature rather than asserted by a client header.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    tenant_id: uuid.UUID
    subject: str
    roles: frozenset[str]

    def has_role(self, role: str) -> bool:
        return role in self.roles


@runtime_checkable
class TokenVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedIdentity:
        """Verify a bearer token and return the identity, or raise AuthenticationError."""


@runtime_checkable
class TokenIssuer(Protocol):
    def issue(
        self,
        tenant_id: uuid.UUID,
        subject: str,
        roles: frozenset[str],
        ttl_seconds: int,
    ) -> str: ...
