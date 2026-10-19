"""
Structured URL text extraction errors shared by URL text and GROBID modules.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class UrlTextExtractionError(RuntimeError):
    """
    Structured URL extraction error.

    :ivar code: Stable machine-readable error code.
    :vartype code: str
    :ivar message: Human-readable error message.
    :vartype message: str
    :ivar details: Optional diagnostic details.
    :vartype details: dict[str, Any]
    """

    def __init__(self, *, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = str(code)
        self.message = str(message)
        self.details = dict(details or {})
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Render this error as a JSON-serializable object.

        :return: Structured error payload.
        :rtype: dict[str, Any]
        """
        payload: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload
