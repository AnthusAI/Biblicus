"""
Shared request validation and corpus opening for the typed Biblicus application programming interface.
"""

from __future__ import annotations

from typing import Any, Type, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from ..command_failure import InvalidRequestError
from ..corpus import Corpus

RequestModelType = TypeVar("RequestModelType", bound=BaseModel)


class ApiRequestModel(BaseModel):
    """
    Base class for typed application programming interface requests.

    Unknown fields are rejected so a misspelled field is reported instead of ignored.
    """

    model_config = ConfigDict(extra="forbid")


class ApiResponseModel(BaseModel):
    """
    Base class for typed application programming interface responses that are not reused library models.
    """

    model_config = ConfigDict(extra="forbid")


def format_validation_error(command_label: str, error: ValidationError) -> str:
    """
    Render a validation error as a single clear sentence naming each offending field.

    :param command_label: Human-readable command name, for example ``taxonomy discover``.
    :type command_label: str
    :param error: Validation error raised while building a request model.
    :type error: pydantic.ValidationError
    :return: Message describing every invalid field.
    :rtype: str
    """
    problems = []
    for problem in error.errors():
        location = ".".join(str(part) for part in problem["loc"]) or "request"
        problems.append(f"{location}: {problem['msg']}")
    return f"Invalid {command_label} request: " + "; ".join(problems)


def validate_request(
    request_type: Type[RequestModelType], command_label: str, **fields: Any
) -> RequestModelType:
    """
    Build a request model from keyword fields and convert validation failures to clear errors.

    :param request_type: Request model class to instantiate.
    :type request_type: type[pydantic.BaseModel]
    :param command_label: Human-readable command name used in error messages.
    :type command_label: str
    :param fields: Field values for the request model.
    :type fields: Any
    :return: Validated request model.
    :rtype: pydantic.BaseModel
    :raises InvalidRequestError: If the fields do not satisfy the request model.
    """
    try:
        return request_type(**fields)
    except ValidationError as error:
        raise InvalidRequestError(format_validation_error(command_label, error)) from error


def open_request_corpus(corpus_path: str) -> Corpus:
    """
    Open the corpus named by a request.

    :param corpus_path: Corpus path or uniform resource identifier.
    :type corpus_path: str
    :return: Opened corpus.
    :rtype: Corpus
    """
    return Corpus.open(corpus_path)
