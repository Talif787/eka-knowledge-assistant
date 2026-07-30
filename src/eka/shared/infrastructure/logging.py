"""Structured logging configuration using structlog.

Emits JSON in non-development environments and binds the correlation id from
the context so every log line is traceable to a request.
"""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(*, level: str = "INFO", json_logs: bool = True) -> None:
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer()
    )

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
