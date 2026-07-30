"""Reusable pagination and sorting primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Generic, TypeVar

from eka.shared.domain.errors import ValidationError

DEFAULT_LIMIT = 20
MAX_LIMIT = 100

T = TypeVar("T")


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class Sort:
    field: str
    direction: SortDirection = SortDirection.DESC


@dataclass(frozen=True, slots=True)
class PageRequest:
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    sort: Sort | None = None

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > MAX_LIMIT:
            raise ValidationError(f"limit must be between 1 and {MAX_LIMIT}")
        if self.offset < 0:
            raise ValidationError("offset must be non-negative")


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: list[T] = field(default_factory=list)
    total: int = 0
    limit: int = DEFAULT_LIMIT
    offset: int = 0

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total
