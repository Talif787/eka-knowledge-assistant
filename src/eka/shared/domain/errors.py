"""Domain error hierarchy.

Errors carry a stable machine-readable code so the presentation layer can map
them to transport-specific responses without leaking internals.
"""
from __future__ import annotations


class DomainError(Exception):
    code: str = "domain_error"

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(DomainError):
    code = "validation_error"


class InvariantViolation(DomainError):
    code = "invariant_violation"


class StateTransitionError(DomainError):
    code = "invalid_state_transition"


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class AuthenticationError(DomainError):
    code = "authentication_error"
