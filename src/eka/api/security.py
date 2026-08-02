"""Authentication wiring for the API.

Turns a bearer token into an AuthenticatedIdentity. The verifier and issuer are
built from settings (they are stateless), so this works in tests without running
the application lifespan. Missing or invalid credentials raise AuthenticationError,
which the error handler maps to 401.
"""
from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from eka.config import get_settings
from eka.modules.identity.domain.identity import (
    AuthenticatedIdentity,
    TokenIssuer,
    TokenVerifier,
)
from eka.modules.identity.infrastructure.jwt import JwtTokenIssuer, JwtTokenVerifier
from eka.shared.domain.errors import AuthenticationError

_bearer_scheme = HTTPBearer(auto_error=False)


def get_token_verifier() -> TokenVerifier:
    settings = get_settings()
    return JwtTokenVerifier(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
    )


def get_token_issuer() -> TokenIssuer:
    settings = get_settings()
    return JwtTokenIssuer(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
    )


def get_current_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    verifier: TokenVerifier = Depends(get_token_verifier),
) -> AuthenticatedIdentity:
    # Prefer the standard Authorization bearer; fall back to X-EKA-Token, which
    # survives environments (like Codespaces port tunnels) that consume the
    # Authorization header for their own auth.
    token = (
        credentials.credentials
        if credentials is not None
        else request.headers.get("X-EKA-Token")
    )
    if not token:
        raise AuthenticationError("missing bearer token")
    return verifier.verify(token)
