"""Transport schemas for the dev token endpoint."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class TokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    subject: str = Field(default="dev-user", min_length=1)
    roles: list[str] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
