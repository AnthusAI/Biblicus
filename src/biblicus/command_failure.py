"""
The failure envelope that every typed Biblicus command prints when it fails.

A typed command is one that has a request model, a response model and a published schema in the
typed application programming interface. When such a command fails, the command-line interface
prints one :class:`CommandFailure` as JSON on standard output and exits with a status that
separates a rejected request from a failed operation.
"""

from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import BaseModel, ConfigDict, Field

INVALID_INPUT_EXIT_STATUS = 2
OPERATION_FAILED_EXIT_STATUS = 1

INVALID_INPUT_FAILURE_CODES = frozenset(
    {
        "invalid_input_json",
        "missing_source_uri",
        "missing_input",
        "invalid_input",
        "input_too_large",
        "invalid_request",
    }
)
OPERATION_FAILED_CODE = "operation_failed"
INVALID_REQUEST_CODE = "invalid_request"


class CommandFailureError(BaseModel):
    """
    The error carried by a command failure.

    :ivar code: Stable machine-readable failure code.
    :vartype code: str
    :ivar message: Human-readable explanation that never contains secrets or source text.
    :vartype message: str
    :ivar details: Optional structured diagnostics, empty when there are none.
    :vartype details: dict[str, Any]
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: Dict[str, Any] = Field(default_factory=dict)


class CommandFailure(BaseModel):
    """
    The single JSON object a typed command prints on standard output when it fails.

    :ivar status: Always ``failed``.
    :vartype status: str
    :ivar error: Code, message and details describing the failure.
    :vartype error: CommandFailureError
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["failed"] = "failed"
    error: CommandFailureError

    @property
    def exit_status(self) -> int:
        """
        Exit status the command-line interface uses for this failure.

        :return: ``2`` when the failure code names a rejected request, otherwise ``1``.
        :rtype: int
        """
        if self.error.code in INVALID_INPUT_FAILURE_CODES:
            return INVALID_INPUT_EXIT_STATUS
        return OPERATION_FAILED_EXIT_STATUS


class CommandFailureException(Exception):
    """
    Raised by a typed command to stop with a structured failure.

    :ivar failure: The envelope the command-line interface prints.
    :vartype failure: CommandFailure
    """

    def __init__(self, *, code: str, message: str, details: Dict[str, Any] | None = None):
        self.failure = CommandFailure(
            error=CommandFailureError(code=code, message=message, details=dict(details or {}))
        )
        super().__init__(message)


def raise_for_error_payload(error_payload: Dict[str, Any]) -> None:
    """
    Raise the structured failure described by a failed response model's ``error`` object.

    :param error_payload: The ``error`` mapping of a failed response, with ``code``, ``message``
        and optionally ``details``.
    :type error_payload: dict[str, Any]
    :return: None.
    :rtype: None
    :raises CommandFailureException: Always, carrying the code, message and details.
    """
    raise CommandFailureException(
        code=error_payload["code"],
        message=error_payload["message"],
        details=error_payload.get("details"),
    )
