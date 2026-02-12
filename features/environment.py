from __future__ import annotations

import builtins
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
    try:
        from biblicus.extractors.paddleocr_vl_text import PaddleOcrVlExtractor

        PaddleOcrVlExtractor._model_cache = {}
    except Exception:
        pass

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
    if hasattr(context, "fake_openai_embeddings"):
        del context.fake_openai_embeddings
    if hasattr(context, "fake_bertopic_behavior"):
        del context.fake_bertopic_behavior
    if hasattr(context, "fake_hmmlearn_behavior"):
        del context.fake_hmmlearn_behavior
    if hasattr(context, "fake_aldea_transcriptions"):
        del context.fake_aldea_transcriptions
    for attr in [
        "_fake_paddleocr_layout_empty",
        "_fake_paddleocr_layout_missing_coordinates",
        "_fake_paddleocr_layout_non_dict",
        "_fake_paddleocr_layout_no_image",
        "_fake_heron_empty_results",
        "_fake_heron_image_none",
    ]:
        setattr(context, attr, False)
    for attr in [
        "_fake_spacy_relations_installed",
        "_fake_spacy_short_installed",
        "_fake_spacy_short_relations_installed",
        "_fake_spacy_short_relations_no_lemma",
    ]:
        setattr(context, attr, False)
    context._fake_docker_installed = False
    context.fake_docker_state = None
    context.fake_docker_log = None
    spacy_original = getattr(context, "_fake_spacy_relations_original_module", None)
    if spacy_original is None:
        spacy_original = getattr(context, "_fake_spacy_short_original_module", None)
    if spacy_original is None:
        spacy_original = getattr(context, "_fake_spacy_short_relations_original_module", None)
    if spacy_original is not None:
        sys.modules["spacy"] = spacy_original
    else:
        sys.modules.pop("spacy", None)
    context._fake_spacy_relations_original_module = None
    context._fake_spacy_short_original_module = None
    context._fake_spacy_short_relations_original_module = None
    context._fake_tesseract_installed = False
    context._fake_tesseract_original_modules = {}

    context._tmp = tempfile.TemporaryDirectory(prefix="biblicus-bdd-")
    context.workdir = Path(context._tmp.name)
    context.repo_root = _repo_root()
    context.env = dict(os.environ)
    context.extra_env = {}
    context.last_result = None
    context.last_ingest = None
    context.last_shown = None
    context.last_source = None
    context.ingested_ids = []
    context.ingested_relpaths = []
    context.ingested_sources = []


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
    if getattr(context, "_fake_dspy_installed", False):
        original_modules = getattr(context, "_fake_dspy_original_modules", {})
        if "dspy" in original_modules:
            sys.modules["dspy"] = original_modules["dspy"]
        else:
            sys.modules.pop("dspy", None)
        context._fake_dspy_installed = False
        context._fake_dspy_original_modules = {}
    if getattr(context, "_fake_litellm_installed", False):
        original_modules = getattr(context, "_fake_litellm_original_modules", {})
        if "litellm" in original_modules:
            sys.modules["litellm"] = original_modules["litellm"]
        else:
            sys.modules.pop("litellm", None)
        context._fake_litellm_installed = False
        context._fake_litellm_original_modules = {}
    if getattr(context, "_fake_dspy_unavailable_installed", False):
        original_modules = getattr(context, "_fake_dspy_unavailable_original_modules", {})
        for name in ["dspy", "litellm"]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_dspy_unavailable_installed = False
        context._fake_dspy_unavailable_original_modules = {}
    if getattr(context, "_fake_dspy_missing_installed", False):
        original_modules = getattr(context, "_fake_dspy_missing_original_modules", {})
        if "dspy" in original_modules:
            sys.modules["dspy"] = original_modules["dspy"]
        else:
            sys.modules.pop("dspy", None)
        context._fake_dspy_missing_installed = False
        context._fake_dspy_missing_original_modules = {}
    if getattr(context, "_fake_hmmlearn_installed", False):
        original_modules = getattr(context, "_fake_hmmlearn_original_modules", {})
        for name in [
            "hmmlearn.hmm",
            "hmmlearn",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_hmmlearn_installed = False
        context._fake_hmmlearn_original_modules = {}
    if getattr(context, "_fake_hmmlearn_unavailable_installed", False):
        original_modules = getattr(context, "_fake_hmmlearn_unavailable_original_modules", {})
        for name in [
            "hmmlearn.hmm",
            "hmmlearn",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_hmmlearn_unavailable_installed = False
        context._fake_hmmlearn_unavailable_original_modules = {}
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
    if getattr(context, "_fake_neo4j_installed", False):
        original_module = getattr(context, "_fake_neo4j_original_module", None)
        if original_module is None:
            sys.modules.pop("neo4j", None)
        else:
            sys.modules["neo4j"] = original_module
        context._fake_neo4j_installed = False
        context._fake_neo4j_original_module = None
    if getattr(context, "_fake_spacy_installed", False):
        original_module = getattr(context, "_fake_spacy_original_module", None)
        if original_module is None:
            sys.modules.pop("spacy", None)
        else:
            sys.modules["spacy"] = original_module
        context._fake_spacy_installed = False
        context._fake_spacy_original_module = None
    if getattr(context, "_fake_tesseract_installed", False):
        original_modules = getattr(context, "_fake_tesseract_original_modules", {})
        for name in ["pytesseract", "PIL", "PIL.Image"]:
            if name in original_modules:
                module = original_modules[name]
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module
            else:
                sys.modules.pop(name, None)
        context._fake_tesseract_installed = False
        context._fake_tesseract_original_modules = {}
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
    if getattr(context, "_aldea_post_patcher", None) is not None:
        try:
            context._aldea_post_patcher.stop()
        except Exception:
            pass
        context._aldea_post_patcher = None
    if getattr(context, "_fake_aldea_unavailable_installed", False):
        original_modules = getattr(context, "_fake_aldea_unavailable_original_modules", {})
        for name in ["httpx"]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_aldea_unavailable_installed = False
        context._fake_aldea_unavailable_original_modules = {}
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
            "docling.datamodel.pipeline_options",
            "docling.datamodel",
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
            "docling.datamodel.pipeline_options",
            "docling.datamodel",
            "docling",
        ]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_docling_unavailable_installed = False
        context._fake_docling_unavailable_original_modules = {}
    if getattr(context, "_fake_heron_installed", False):
        original_modules = getattr(context, "_fake_heron_original_modules", {})
        for name in ["transformers", "torch", "PIL", "PIL.Image"]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_heron_installed = False
        context._fake_heron_original_modules = {}
    if getattr(context, "_fake_heron_import_blocked", False):
        original_import = getattr(context, "_fake_heron_original_import", None)
        if original_import is not None:
            builtins.__import__ = original_import
        original_transformers = getattr(context, "_fake_heron_original_transformers", None)
        if original_transformers is not None:
            sys.modules["transformers"] = original_transformers
        original_torch = getattr(context, "_fake_heron_original_torch", None)
        if original_torch is not None:
            sys.modules["torch"] = original_torch
        context._fake_heron_import_blocked = False
        context._fake_heron_original_import = None
        context._fake_heron_original_transformers = None
        context._fake_heron_original_torch = None
    if getattr(context, "_fake_paddleocr_layout_installed", False):
        original_modules = getattr(context, "_fake_paddleocr_layout_original_modules", {})
        for name in ["paddleocr", "cv2"]:
            if name in original_modules:
                sys.modules[name] = original_modules[name]
            else:
                sys.modules.pop(name, None)
        context._fake_paddleocr_layout_installed = False
        context._fake_paddleocr_layout_original_modules = {}
    if getattr(context, "_fake_paddleocr_layout_import_blocked", False):
        original_import = getattr(context, "_fake_paddleocr_layout_original_import", None)
        if original_import is not None:
            builtins.__import__ = original_import
        original_module = getattr(context, "_fake_paddleocr_layout_original_module", None)
        if original_module is not None:
            sys.modules["paddleocr"] = original_module
        context._fake_paddleocr_layout_import_blocked = False
        context._fake_paddleocr_layout_original_import = None
        context._fake_paddleocr_layout_original_module = None
    if getattr(context, "_fake_spacy_relations_installed", False):
        original_module = getattr(context, "_fake_spacy_relations_original_module", None)
        if original_module is not None:
            sys.modules["spacy"] = original_module
        else:
            sys.modules.pop("spacy", None)
        context._fake_spacy_relations_installed = False
        context._fake_spacy_relations_original_module = None
    if getattr(context, "_fake_spacy_short_installed", False):
        original_module = getattr(context, "_fake_spacy_short_original_module", None)
        if original_module is not None:
            sys.modules["spacy"] = original_module
        else:
            sys.modules.pop("spacy", None)
        context._fake_spacy_short_installed = False
        context._fake_spacy_short_original_module = None
    if getattr(context, "_fake_spacy_short_relations_installed", False):
        original_module = getattr(context, "_fake_spacy_short_relations_original_module", None)
        if original_module is not None:
            sys.modules["spacy"] = original_module
        else:
            sys.modules.pop("spacy", None)
        context._fake_spacy_short_relations_installed = False
        context._fake_spacy_short_relations_original_module = None
    if getattr(context, "_spacy_import_blocked", False):
        original_import = getattr(context, "_spacy_original_import", None)
        if original_import is not None:
            builtins.__import__ = original_import
        context._spacy_import_blocked = False
        context._spacy_original_import = None
    original_spacy_module = getattr(context, "_spacy_original_module", None)
    if original_spacy_module is not None:
        sys.modules["spacy"] = original_spacy_module
        context._spacy_original_module = None
    if getattr(context, "_fake_neo4j_internal_installed", False):
        original_module = getattr(context, "_fake_neo4j_internal_original", None)
        if original_module is not None:
            sys.modules["neo4j"] = original_module
        else:
            sys.modules.pop("neo4j", None)
        context._fake_neo4j_internal_installed = False
        context._fake_neo4j_internal_original = None
    if getattr(context, "_tesseract_import_blocked", False):
        original_import = getattr(context, "_tesseract_original_import", None)
        if original_import is not None:
            builtins.__import__ = original_import
        context._tesseract_import_blocked = False
        context._tesseract_original_import = None
    original_tesseract_module = getattr(context, "_tesseract_original_module", None)
    if original_tesseract_module is not None:
        sys.modules["pytesseract"] = original_tesseract_module
        context._tesseract_original_module = None
    if getattr(context, "_tesseract_fake_installed", False):
        original_modules = getattr(context, "_tesseract_original_modules", {})
        if "pytesseract" in original_modules:
            sys.modules["pytesseract"] = original_modules["pytesseract"]
        else:
            sys.modules.pop("pytesseract", None)
        context._tesseract_fake_installed = False
        context._tesseract_original_modules = {}
    editdistance_import_patcher = getattr(context, "_editdistance_import_patcher", None)
    if editdistance_import_patcher is not None:
        original_import = getattr(context, "_editdistance_original_import", None)
        if original_import is not None:
            builtins.__import__ = original_import
            context._editdistance_original_import = None
        context._editdistance_import_patcher = None
    original_editdistance = getattr(context, "_editdistance_original_module", None)
    if original_editdistance is not None:
        sys.modules["editdistance"] = original_editdistance
        context._editdistance_original_module = None
    elif "editdistance" in sys.modules and getattr(context, "_editdistance_original_module", None) is None:
        sys.modules.pop("editdistance", None)
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
