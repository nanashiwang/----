from __future__ import annotations


class WorkflowError(Exception):
    """Base workflow error."""


class PendingUserActionError(WorkflowError):
    """Raised when a flow needs user confirmation before continuing."""


class EvidenceValidationError(WorkflowError):
    """Raised when a recommendation misses mandatory evidence references."""
