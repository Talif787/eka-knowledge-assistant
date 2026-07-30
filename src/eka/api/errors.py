"""HTTP error envelope and exception handlers.

Domain errors are mapped to stable HTTP status codes and a uniform response
shape so clients can handle failures programmatically.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from eka.shared.domain.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    StateTransitionError,
    ValidationError,
)
from eka.shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

_STATUS_BY_CODE: dict[type[DomainError], int] = {
    ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    StateTransitionError: status.HTTP_409_CONFLICT,
    ConflictError: status.HTTP_409_CONFLICT,
    NotFoundError: status.HTTP_404_NOT_FOUND,
}


def _envelope(request: Request, code: str, message: str, details: dict) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    status_code = getattr(request.state, "_status_code", status.HTTP_400_BAD_REQUEST)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "requestId": request_id,
                "details": details,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        request.state._status_code = _STATUS_BY_CODE.get(
            type(exc), status.HTTP_400_BAD_REQUEST
        )
        return _envelope(request, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request.state._status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return _envelope(
            request, "validation_error", "request validation failed", {"errors": exc.errors()}
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", error=str(exc), exc_info=exc)
        request.state._status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return _envelope(request, "internal_error", "an unexpected error occurred", {})
