"""Alembic environment configured for async SQLAlchemy."""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from eka.config import get_settings
from eka.modules.documents.infrastructure import models  # noqa: F401  (register tables)
from eka.modules.ingestion.infrastructure import models as _ingestion_models  # noqa: F401
from eka.shared.infrastructure.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(get_settings().database_dsn)
    async with engine.connect() as connection:
        await connection.run_sync(_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async())


run_migrations_online()
