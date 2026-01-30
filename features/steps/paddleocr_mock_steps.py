from __future__ import annotations

import builtins
import sys
from typing import Any
from unittest import mock

from behave import given


@given("the PaddleOCR library is not available")
def step_paddleocr_not_available(context) -> None:
    """Mock paddleocr import to raise ImportError."""
    original_import = builtins.__import__
    original_modules = {}

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "paddleocr" or name.startswith("paddleocr."):
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    # Remove from sys.modules if present
    for name in list(sys.modules.keys()):
        if name.startswith("paddleocr") or name.startswith("paddlepaddle"):
            original_modules[name] = sys.modules[name]
            del sys.modules[name]

    # Mock __import__
    import_patcher = mock.patch("builtins.__import__", side_effect=mock_import)
    import_patcher.start()

    # Store for cleanup
    context._paddleocr_original_import = original_import
    context._paddleocr_original_modules = original_modules
    context._paddleocr_import_patcher = import_patcher


def cleanup_paddleocr_mock(context) -> None:
    """Restore original paddleocr modules and import."""
    import_patcher = getattr(context, "_paddleocr_import_patcher", None)
    if import_patcher:
        import_patcher.stop()

    original_modules = getattr(context, "_paddleocr_original_modules", None)
    if original_modules:
        for name, module in original_modules.items():
            sys.modules[name] = module
