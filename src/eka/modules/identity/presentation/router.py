"""Auth API (v1).

A development-only endpoint that mints a signed token, standing in for a real
identity provider. It is disabled unless EKA_AUTH_DEV_TOKEN_ENABLED is true; when
disabled it responds 404 so its existence is not advertised in production.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from eka.api.security import get_token_issuer
from eka.config import get_settings
from eka.modules.identity.domain.identity import TokenIssuer
from eka.modules.identity.presentation.schemas import TokenRequest, TokenResponse
from eka.shared.domain.errors import NotFoundError

router = APIRouter(tags=["auth"])


@router.post("/v1/auth/token", response_model=TokenResponse)
async def issue_token(
    body: TokenRequest,
    issuer: TokenIssuer = Depends(get_token_issuer),
) -> TokenResponse:
    settings = get_settings()
    if not settings.auth_dev_token_enabled:
        raise NotFoundError("token endpoint is not available")
    token = issuer.issue(
        tenant_id=body.tenant_id,
        subject=body.subject,
        roles=frozenset(body.roles),
        ttl_seconds=settings.jwt_access_ttl_seconds,
    )
    return TokenResponse(
        access_token=token, expires_in=settings.jwt_access_ttl_seconds
    )
