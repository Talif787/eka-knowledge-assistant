"""Transport schemas for the answer API."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    collection_id: uuid.UUID | None = None
    top_k: int = Field(default=5, ge=1, le=50)
