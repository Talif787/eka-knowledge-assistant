"""Async database engine, session factory, and declarative base."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_engine(dsn: str, *, echo: bool = False, pool_size: int = 10) -> AsyncEngine:
    return create_async_engine(
        dsn,
        echo=echo,
        pool_size=pool_size,
        max_overflow=pool_size,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
