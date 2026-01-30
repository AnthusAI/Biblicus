from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence

from biblicus.cli import main as biblicus_main


def _repo_root() -> Path:
    """
    Resolve the repository root directory.

    :return: Repository root path.
    :rtype: Path
    """
    return Path(__file__).resolve().parent.parent


def before_scenario(context, scenario) -> None:
    """
    Behave hook executed before each scenario.

    :param context: Behave context object.
    :type context: object
    :param scenario: Behave scenario.
    :type scenario: object
    :return: None.
    :rtype: None
    """
    import biblicus.__main__ as _biblicus_main

    _ = _biblicus_main

    # Clear fake module behaviors at the START of each scenario
    # Delete and recreate to ensure fresh state
    if hasattr(context, "fake_rapidocr_behaviors"):
        del context.fake_rapidocr_behaviors
    if hasattr(context, "fake_paddleocr_vl_behaviors"):
        del context.fake_paddleocr_vl_behaviors
    if hasattr(context, "fake_requests_behaviors"):
        del context.fake_requests_behaviors
    if hasattr(context, "fake_docling_behaviors"):
        del context.fake_docling_behaviors
    if hasattr(context, "fake_openai_chat_behaviors"):
        del context.fake_openai_chat_behaviors
    if hasattr(context, "fake_bertopic_behavior"):
        del context.fake_bertopic_behavior

    context._tmp = tempfile.TemporaryDirectory(prefix="biblicus-bdd-")
    context.workdir = Path(context._tmp.name)
    context.repo_root = _repo_root()
    context.env = dict(os.environ)
    context.extra_env = {}
    context.last_result = None
    context.last_ingest = None
    context.last_shown = None
    context.ingested_ids = []


def after_scenario(context, scenario) -> None:
    """
    Behave hook executed after each scenario.

    :param context: Behave context object.
    :type context: object
    :param scenario: Behave scenario.
    :type scenario: object
    :return: None.
    :rtype: None
    """
    if getattr(context, "httpd", None) is not None:
        context.httpd.shutdown()
        context.httpd.server_close()
        context.httpd = None
    if getattr(context, "_fake_unstructured_installed", False):
        original_modules = getattr(context, "_fake_unstructured_original_modules", {})
        for name in [
            "unstructured.partition.auto",
            "unstructured.partition",
            "unstructured",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_unstructured_installed = False
        context._fake_unstructured_original_modules = {}
    if getattr(context, "_fake_unstructured_unavailable_installed", False):
        original_modules = getattr(context, "_fake_unstructured_unavailable_original_modules", {})
        for name in [
            "unstructured.partition.auto",
            "unstructured.partition",
            "unstructured",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_unstructured_unavailable_installed = False
        context._fake_unstructured_unavailable_original_modules = {}
    if getattr(context, "_fake_openai_installed", False):
        original_modules = getattr(context, "_fake_openai_original_modules", {})
        for name in [
            "openai",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_openai_installed = False
        context._fake_openai_original_modules = {}
    if getattr(context, "_fake_openai_unavailable_installed", False):
        original_modules = getattr(context, "_fake_openai_unavailable_original_modules", {})
        for name in [
            "openai",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_openai_unavailable_installed = False
        context._fake_openai_unavailable_original_modules = {}
    if getattr(context, "_fake_bertopic_installed", False):
        original_modules = getattr(context, "_fake_bertopic_original_modules", {})
        if "bertopic" in original_modules:
            sys.modules["bertopic"] = original_modules["bertopic"]
        else:
            sys.modules.pop("bertopic", None)
        context._fake_bertopic_installed = False
        context._fake_bertopic_original_modules = {}
    if getattr(context, "_fake_bertopic_unavailable_installed", False):
        original_modules = getattr(context, "_fake_bertopic_unavailable_original_modules", {})
        if "bertopic" in original_modules:
            sys.modules["bertopic"] = original_modules["bertopic"]
        else:
            sys.modules.pop("bertopic", None)
        context._fake_bertopic_unavailable_installed = False
        context._fake_bertopic_unavailable_original_modules = {}
    if getattr(context, "_fake_sklearn_installed", False):
        original_modules = getattr(context, "_fake_sklearn_original_modules", {})
        for name in [
            "sklearn.feature_extraction.text",
            "sklearn.feature_extraction",
            "sklearn",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_sklearn_installed = False
        context._fake_sklearn_original_modules = {}
    if getattr(context, "_fake_sklearn_unavailable_installed", False):
        original_modules = getattr(context, "_fake_sklearn_unavailable_original_modules", {})
        for name in [
            "sklearn.feature_extraction.text",
            "sklearn.feature_extraction",
            "sklearn",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_sklearn_unavailable_installed = False
        context._fake_sklearn_unavailable_original_modules = {}
    if getattr(context, "_fake_rapidocr_installed", False):
        original_modules = getattr(context, "_fake_rapidocr_original_modules", {})
        for name in [
            "rapidocr_onnxruntime",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_rapidocr_installed = False
        context._fake_rapidocr_original_modules = {}
    if getattr(context, "_fake_rapidocr_unavailable_installed", False):
        original_modules = getattr(context, "_fake_rapidocr_unavailable_original_modules", {})
        for name in [
            "rapidocr_onnxruntime",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_rapidocr_unavailable_installed = False
        context._fake_rapidocr_unavailable_original_modules = {}
    # Clear fake rapidocr behaviors
    if hasattr(context, "fake_rapidocr_behaviors"):
        context.fake_rapidocr_behaviors.clear()
    if getattr(context, "_fake_markitdown_installed", False):
        original_modules = getattr(context, "_fake_markitdown_original_modules", {})
        for name in [
            "markitdown",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_markitdown_installed = False
        context._fake_markitdown_original_modules = {}
    if getattr(context, "_fake_markitdown_unavailable_installed", False):
        original_modules = getattr(context, "_fake_markitdown_unavailable_original_modules", {})
        for name in [
            "markitdown",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_markitdown_unavailable_installed = False
        context._fake_markitdown_unavailable_original_modules = {}
    # Clear fake paddleocr behaviors FIRST (before removing modules)
    if hasattr(context, "fake_paddleocr_vl_behaviors"):
        context.fake_paddleocr_vl_behaviors.clear()
    if getattr(context, "_fake_paddleocr_installed", False):
        # Remove all paddle-related modules
        paddle_module_names = [
            name for name in list(sys.modules.keys()) if "paddle" in name.lower()
        ]
        for name in paddle_module_names:
            sys.modules.pop(name, None)
        # Restore original modules
        original_modules = getattr(context, "_fake_paddleocr_original_modules", {})
        for name, module in original_modules.items():
            sys.modules[name] = module
        context._fake_paddleocr_installed = False
        context._fake_paddleocr_original_modules = {}
    if getattr(context, "_fake_paddleocr_unavailable_installed", False):
        # Remove import hook
        hook = getattr(context, "_fake_paddleocr_import_hook", None)
        if hook is not None and hook in sys.meta_path:
            sys.meta_path.remove(hook)
        # Restore original modules
        original_modules = getattr(context, "_fake_paddleocr_unavailable_original_modules", {})
        for name, module in original_modules.items():
            sys.modules[name] = module
        context._fake_paddleocr_unavailable_installed = False
        context._fake_paddleocr_unavailable_original_modules = {}
        context._fake_paddleocr_import_hook = None
    # Cleanup import patcher from paddleocr_mock_steps
    import_patcher = getattr(context, "_paddleocr_import_patcher", None)
    if import_patcher:
        import_patcher.stop()
        context._paddleocr_import_patcher = None
    # Restore original modules from paddleocr_mock_steps
    original_modules = getattr(context, "_paddleocr_original_modules", None)
    if original_modules:
        for name, module in original_modules.items():
            sys.modules[name] = module
        context._paddleocr_original_modules = {}
    if getattr(context, "_fake_requests_installed", False):
        original_modules = getattr(context, "_fake_requests_original_modules", {})
        for name in ["requests"]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_requests_installed = False
        context._fake_requests_original_modules = {}
    # Clear fake requests behaviors
    if hasattr(context, "fake_requests_behaviors"):
        context.fake_requests_behaviors.clear()
    # Cleanup Docling fake modules
    if getattr(context, "_fake_docling_installed", False):
        original_modules = getattr(context, "_fake_docling_original_modules", {})
        for name in [
            "docling.pipeline_options",
            "docling.document_converter",
            "docling",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_docling_installed = False
        context._fake_docling_original_modules = {}
    if getattr(context, "_fake_docling_unavailable_installed", False):
        original_modules = getattr(context, "_fake_docling_unavailable_original_modules", {})
        for name in [
            "docling.pipeline_options",
            "docling.document_converter",
            "docling",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_docling_unavailable_installed = False
        context._fake_docling_unavailable_original_modules = {}
    # Clear fake docling behaviors
    if hasattr(context, "fake_docling_behaviors"):
        context.fake_docling_behaviors.clear()
    original_sys_version_info = getattr(context, "_original_sys_version_info", None)
    if original_sys_version_info is not None:
        sys.version_info = original_sys_version_info
        context._original_sys_version_info = None
    if hasattr(context, "_tmp"):
        context._tmp.cleanup()


@dataclass
class RunResult:
    """
    Captured command-line interface execution result.

    :ivar returncode: Process exit code.
    :vartype returncode: int
    :ivar stdout: Captured standard output.
    :vartype stdout: str
    :ivar stderr: Captured standard error.
    :vartype stderr: str
    """

    returncode: int
    stdout: str
    stderr: str


def run_biblicus(
    context,
    args: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    input_text: Optional[str] = None,
    extra_env: Optional[Dict[str, str]] = None,
) -> RunResult:
    """
    Run the Biblicus command-line interface in-process for coverage capture.

    :param context: Behave context object.
    :type context: object
    :param args: Command-line interface argument list.
    :type args: Sequence[str]
    :param cwd: Optional working directory.
    :type cwd: Path or None
    :param input_text: Optional standard input content.
    :type input_text: str or None
    :param extra_env: Optional environment overrides.
    :type extra_env: dict[str, str] or None
    :return: Captured execution result.
    :rtype: RunResult
    """
    import contextlib
    import io

    out = io.StringIO()
    err = io.StringIO()

    prev_cwd = os.getcwd()
    prev_stdin = sys.stdin

    prior_env: dict[str, Optional[str]] = {}
    if extra_env:
        for k, v in extra_env.items():
            prior_env[k] = os.environ.get(k)
            os.environ[k] = v

    try:
        os.chdir(str(cwd or context.workdir))
        if input_text is not None:
            sys.stdin = io.StringIO(input_text)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = int(biblicus_main(list(args)) or 0)
            except SystemExit as e:
                if isinstance(e.code, int):
                    code = e.code
                else:
                    code = 1
    finally:
        os.chdir(prev_cwd)
        sys.stdin = prev_stdin
        for k, v in prior_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    result = RunResult(returncode=code, stdout=out.getvalue(), stderr=err.getvalue())
    context.last_result = result
    return result
