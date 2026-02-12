from __future__ import annotations

import argparse
import builtins
import json
import sqlite3
import sys
from pathlib import Path
from typing import List

import numpy as np
from behave import given, then, when

from biblicus.corpus import Corpus
from biblicus.embedding_providers import EmbeddingProviderConfig, HashEmbeddingProvider
from biblicus.models import Evidence, QueryBudget, parse_extraction_snapshot_reference
from biblicus.graph.extractors.simple_entities import _extract_entities
from biblicus.ai.models import LlmClientConfig
from biblicus.text import extract as text_extract_module
from biblicus.text.extract import TextExtractRequest, apply_text_extract
from biblicus.retrieval import apply_budget, create_configuration_manifest, create_snapshot_manifest
from biblicus.retrievers.embedding_index_common import (
    ChunkRecord,
    EmbeddingIndexConfiguration,
    _build_snippet as build_embedding_snippet,
    _extract_span_text,
    _load_text_from_item as load_embedding_text,
    resolve_extraction_reference,
)
from biblicus.retrievers.embedding_index_file import (
    EmbeddingIndexFileRetriever,
    _candidate_limit as embedding_candidate_limit,
    _build_evidence,
    _top_indices_batched,
)
from biblicus.retrievers.embedding_index_inmemory import EmbeddingIndexInMemoryRetriever
from biblicus.retrievers.hybrid import (
    HybridConfiguration,
    HybridRetriever,
    _ensure_retriever_supported,
    _expand_component_budget,
    _fuse_evidence,
)
from biblicus.retrievers.sqlite_full_text_search import (
    SqliteFullTextSearchConfiguration,
    SqliteFullTextSearchRetriever,
    _apply_rerank_if_enabled,
    _apply_stop_words,
    _build_full_text_search_index,
    _candidate_limit as sqlite_candidate_limit,
    _create_full_text_search_schema,
    _ensure_full_text_search_version_five,
    _iter_chunks,
    _query_full_text_search_index,
    _rank_candidates,
    _resolve_snapshot_db_path,
    _resolve_stop_words,
    _resolve_extraction_reference as resolve_sqlite_reference,
    _tokenize_query,
)
from biblicus.retrievers.tf_vector import (
    TfVectorConfiguration,
    TfVectorRetriever,
    _build_snippet as build_tf_snippet,
    _count_text_items as count_tf_text_items,
    _cosine_similarity,
    _find_first_match,
    _load_text_from_item as load_tf_text,
    _resolve_extraction_reference as resolve_tf_reference,
    _score_items,
    _term_frequencies,
    _tokenize_text,
    _vector_norm,
)
from biblicus.retrievers.scan import (
    ScanConfiguration,
    ScanRetriever,
    _build_snippet as build_scan_snippet,
    _count_text_items as count_scan_text_items,
    _find_first_match as find_scan_match,
    _load_text_from_item as load_scan_text,
    _resolve_extraction_reference as resolve_scan_reference,
    _score_items as score_scan_items,
)
from biblicus.extraction import (
    ExtractionItemResult,
    build_extraction_snapshot,
    create_extraction_configuration_manifest,
    create_extraction_snapshot_manifest,
    write_extraction_snapshot_manifest,
)
from biblicus.extractors import get_extractor as resolve_extractor
from biblicus.extractors.pipeline import PipelineExtractorConfig, PipelineStageSpec
from biblicus.extractors.docling_granite_text import DoclingGraniteExtractor
from biblicus.extractors.docling_smol_text import DoclingSmolExtractor
from biblicus.workflow import (
    Plan,
    Task,
    _find_extraction_snapshot,
    _find_retrieval_snapshot,
    _flatten_tasks,
    build_default_handler_registry,
    build_plan_for_index,
    build_plan_for_load,
    build_plan_for_query,
    normalize_task_kind,
)


def _corpus_path(context, name: str) -> Path:
    workdir = getattr(context, "workdir", None)
    if workdir is None:
        raise AssertionError("Missing workdir in test context")
    return (workdir / name).resolve()


def _resolve_fixture_path(context, filename: str) -> Path:
    """Resolve fixture path, accounting for corpus root if set."""
    candidate = Path(filename)
    if candidate.is_absolute():
        return candidate
    workdir_path = (context.workdir / candidate).resolve()
    if candidate.parts and candidate.parts[0] == ".biblicus":
        return workdir_path
    corpus_root = getattr(context, "last_corpus_root", None)
    if corpus_root is not None:
        if candidate.parts and candidate.parts[0] == corpus_root.name:
            return workdir_path
        return (corpus_root / candidate).resolve()
    return workdir_path


@given('a markdown file "{filename}" exists with contents "{contents}"')
def step_markdown_file_exists(context, filename: str, contents: str) -> None:
    path = context.workdir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


@when("I exercise workflow dependency edge cases")
def step_workflow_dependency_edge_cases(context) -> None:
    corpus = Corpus.open(_corpus_path(context, "corpus"))
    invalid_path = corpus.snapshots_dir / "invalid.json"
    corpus.snapshots_dir.mkdir(parents=True, exist_ok=True)
    invalid_path.write_text("not-json", encoding="utf-8")
    plan = build_plan_for_index(corpus, "scan", load_handler_available=True)
    assert plan.status in {"ready", "complete"}
    assert normalize_task_kind("  fetch ") == "load"

    assert normalize_task_kind("") == ""

    load_plan = build_plan_for_load(corpus, handler_available=True)
    assert load_plan.execute(mode="dry_run") == []

    try:
        load_plan.execute(mode="invalid")
        raise AssertionError("Expected invalid mode to raise")
    except ValueError:
        pass

    handler_registry = build_default_handler_registry(corpus)
    extract_task = Task(
        name="extract",
        kind="extract",
        target_type="corpus",
        target_id=corpus.uri,
        status="ready",
        metadata={"pipeline": {"stages": [{"extractor_id": "pass-through-text", "configuration": {}}]}},
    )
    extract_plan = Plan(tasks=[extract_task], root=extract_task, status="ready")
    assert extract_plan.execute(
        mode="prompt", handler_registry=handler_registry, prompt_handler=lambda task: True
    )
    try:
        load_plan.execute(mode="prompt", prompt_handler=lambda task: False)
        raise AssertionError("Expected prompt decline to raise")
    except RuntimeError:
        pass

    try:
        load_plan.execute(mode="auto", handler_registry={})
        raise AssertionError("Expected missing handler to raise")
    except RuntimeError:
        assert "load" in load_plan.missing_handlers

    blocked_plan = build_plan_for_load(corpus, handler_available=False)
    try:
        blocked_plan.execute(mode="auto", handler_registry={})
        raise AssertionError("Expected blocked plan to raise")
    except RuntimeError:
        pass

    task = Task(
        name="blocked",
        kind="load",
        target_type="corpus",
        target_id=corpus.uri,
        status="blocked",
        reason="blocked",
    )
    manual_plan = Plan(tasks=[task], root=task, status="blocked")
    try:
        manual_plan.execute(mode="auto", handler_registry={})
        raise AssertionError("Expected manual blocked plan to raise")
    except RuntimeError:
        pass

    retriever_config = create_configuration_manifest(
        retriever_id="scan",
        name="default",
        configuration={},
    )
    retrieval_snapshot = create_snapshot_manifest(corpus, configuration=retriever_config, stats={})
    corpus.write_snapshot(retrieval_snapshot)
    mismatch = _find_retrieval_snapshot(
        corpus=corpus,
        retriever_id="tf-vector",
        configuration_id=retriever_config.configuration_id,
        catalog_generated_at=retrieval_snapshot.catalog_generated_at,
    )
    assert mismatch is None
    mismatch = _find_retrieval_snapshot(
        corpus=corpus,
        retriever_id="scan",
        configuration_id="different",
        catalog_generated_at=retrieval_snapshot.catalog_generated_at,
    )
    assert mismatch is None
    mismatch = _find_retrieval_snapshot(
        corpus=corpus,
        retriever_id="scan",
        configuration_id=retriever_config.configuration_id,
        catalog_generated_at="different",
    )
    assert mismatch is None

    extraction_config = create_extraction_configuration_manifest(
        extractor_id="pipeline",
        name="default",
        configuration={"stages": [{"extractor_id": "pass-through-text", "configuration": {}}]},
    )
    extraction_manifest = create_extraction_snapshot_manifest(
        corpus, configuration=extraction_config
    )
    extraction_reference = corpus.extraction_snapshot_dir(
        extractor_id="pipeline", snapshot_id=extraction_manifest.snapshot_id
    )
    extraction_reference.mkdir(parents=True, exist_ok=True)
    write_extraction_snapshot_manifest(
        snapshot_dir=extraction_reference, manifest=extraction_manifest
    )
    entry = _find_extraction_snapshot(
        corpus=corpus,
        configuration_id="missing",
        catalog_generated_at=extraction_manifest.catalog_generated_at,
    )
    assert entry is None
    entry = _find_extraction_snapshot(
        corpus=corpus,
        configuration_id=extraction_manifest.configuration.configuration_id,
        catalog_generated_at="missing",
    )
    assert entry is None
    entry = _find_extraction_snapshot(
        corpus=corpus,
        configuration_id=extraction_manifest.configuration.configuration_id,
        catalog_generated_at=extraction_manifest.catalog_generated_at,
    )
    assert entry is not None

    child_task = Task(
        name="child",
        kind="extract",
        target_type="corpus",
        target_id=corpus.uri,
        status="ready",
    )
    flattened = _flatten_tasks(child_task, seen={id(child_task)})
    assert child_task not in flattened

    query_plan = build_plan_for_query(corpus, "scan", load_handler_available=False)
    assert query_plan.status in {"ready", "blocked"}

    import biblicus.workflow as workflow_module

    blocked_task = Task(
        name="extract",
        kind="extract",
        target_type="corpus",
        target_id=corpus.uri,
        status="blocked",
        reason="blocked",
    )
    blocked_plan = Plan(tasks=[blocked_task], root=blocked_task, status="blocked")
    original_build_plan = workflow_module.build_plan_for_extract
    try:
        workflow_module.build_plan_for_extract = lambda *args, **kwargs: blocked_plan
        blocked_index_plan = build_plan_for_index(corpus, "scan", load_handler_available=False)
        assert blocked_index_plan.status == "blocked"
        blocked_query_plan = build_plan_for_query(corpus, "scan", load_handler_available=False)
        assert blocked_query_plan.status == "blocked"
    finally:
        workflow_module.build_plan_for_extract = original_build_plan


@then("the workflow dependency edge cases succeed")
def step_workflow_dependency_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise CLI dependency edge cases")
def step_cli_dependency_edge_cases(context) -> None:
    from biblicus import cli as cli_module

    corpus = Corpus.open(_corpus_path(context, "corpus"))

    try:
        cli_module._dependency_mode(
            argparse.Namespace(auto_deps=True, no_deps=True),
        )
        raise AssertionError("Expected conflicting dependency flags to raise")
    except ValueError:
        pass

    class DummyStdin:
        def __init__(self, is_tty: bool) -> None:
            self._is_tty = is_tty

        def isatty(self) -> bool:
            return self._is_tty

        def read(self) -> str:
            return ""

    original_stdin = sys.stdin
    try:
        sys.stdin = DummyStdin(is_tty=False)
        assert (
            cli_module._dependency_mode(
                argparse.Namespace(auto_deps=False, no_deps=False),
            )
            == "auto"
        )
        sys.stdin = DummyStdin(is_tty=True)
        assert (
            cli_module._dependency_mode(
                argparse.Namespace(auto_deps=False, no_deps=False),
            )
            == "prompt"
        )
    finally:
        sys.stdin = original_stdin

    ready_task = Task(
        name="extract",
        kind="extract",
        target_type="corpus",
        target_id=corpus.uri,
        status="ready",
    )
    ready_plan = Plan(tasks=[ready_task], root=ready_task, status="ready")

    original_input = builtins.input
    try:
        builtins.input = lambda _: "y"
        assert cli_module._prompt_dependency_plan(ready_plan, "index")
        builtins.input = lambda _: "n"
        try:
            cli_module._execute_dependency_plan(
                ready_plan, corpus=corpus, label="index", mode="prompt"
            )
            raise AssertionError("Expected prompt decline to raise")
        except ValueError:
            pass
    finally:
        builtins.input = original_input

    complete_task = Task(
        name="extract",
        kind="extract",
        target_type="corpus",
        target_id=corpus.uri,
        status="complete",
    )
    complete_plan = Plan(tasks=[complete_task], root=complete_task, status="complete")
    assert (
        cli_module._execute_dependency_plan(
            complete_plan, corpus=corpus, label="index", mode="auto"
        )
        == []
    )

    blocked_task = Task(
        name="extract",
        kind="extract",
        target_type="corpus",
        target_id=corpus.uri,
        status="blocked",
        reason="blocked",
    )
    blocked_plan = Plan(tasks=[blocked_task], root=blocked_task, status="blocked")
    try:
        cli_module._execute_dependency_plan(
            blocked_plan, corpus=corpus, label="index", mode="auto"
        )
        raise AssertionError("Expected blocked plan to raise")
    except ValueError:
        pass

    try:
        cli_module._execute_dependency_plan(
            ready_plan, corpus=corpus, label="index", mode="none"
        )
        raise AssertionError("Expected no-deps plan to raise")
    except ValueError:
        pass

    try:
        cli_module._execute_dependency_plan(
            ready_plan, corpus=corpus, label="index", mode="invalid"
        )
        raise AssertionError("Expected invalid dependency mode to raise")
    except ValueError:
        pass

    query_task = Task(
        name="query",
        kind="query",
        target_type="retriever",
        target_id="scan",
        status="ready",
    )
    query_plan = Plan(tasks=[query_task], root=query_task, status="ready")
    assert (
        cli_module._execute_dependency_plan(
            query_plan, corpus=corpus, label="query", mode="auto"
        )
        == []
    )
    query_dependency = Task(
        name="extract",
        kind="extract",
        target_type="corpus",
        target_id=corpus.uri,
        status="ready",
        metadata={"pipeline": {"stages": [{"extractor_id": "pass-through-text", "configuration": {}}]}},
    )
    query_root = Task(
        name="query",
        kind="query",
        target_type="retriever",
        target_id="scan",
        status="ready",
        depends_on=[query_dependency],
    )
    query_plan_with_deps = Plan(
        tasks=[query_dependency, query_root],
        root=query_root,
        status="ready",
    )
    cli_module._execute_dependency_plan(
        query_plan_with_deps, corpus=corpus, label="query", mode="auto"
    )

    import biblicus.workflow as workflow_module

    original_build_plan = workflow_module.build_plan_for_query
    try:
        complete_query_task = Task(
            name="query",
            kind="query",
            target_type="retriever",
            target_id="scan",
            status="complete",
        )
        workflow_module.build_plan_for_query = lambda *args, **kwargs: Plan(
            tasks=[complete_query_task], root=complete_query_task, status="complete"
        )
        args = argparse.Namespace(
            corpus=str(corpus.root),
            snapshot=None,
            retriever=None,
            query="test",
            max_total_items=1,
            maximum_total_characters=10,
            max_items_per_source=1,
            offset=0,
            reranker_id=None,
            minimum_score=None,
            auto_deps=True,
            no_deps=False,
        )
        try:
            cli_module.cmd_query(args)
            raise AssertionError("Expected query without snapshot to raise")
        except ValueError:
            pass
    finally:
        workflow_module.build_plan_for_query = original_build_plan


@then("the CLI dependency edge cases succeed")
def step_cli_dependency_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise retrieval budget edge cases")
def step_retrieval_budget_edge_cases(context) -> None:
    evidence = [
        Evidence(
            item_id="a",
            source_uri="src-1",
            media_type="text/plain",
            score=1.0,
            rank=1,
            text="alpha",
            content_ref=None,
            span_start=None,
            span_end=None,
            stage="test",
            configuration_id="",
            snapshot_id="",
            metadata={},
            hash="",
        ),
        Evidence(
            item_id="b",
            source_uri="src-1",
            media_type="text/plain",
            score=0.9,
            rank=1,
            text="beta",
            content_ref=None,
            span_start=None,
            span_end=None,
            stage="test",
            configuration_id="",
            snapshot_id="",
            metadata={},
            hash="",
        ),
        Evidence(
            item_id="c",
            source_uri="src-2",
            media_type="text/plain",
            score=0.8,
            rank=1,
            text="gamma",
            content_ref=None,
            span_start=None,
            span_end=None,
            stage="test",
            configuration_id="",
            snapshot_id="",
            metadata={},
            hash="",
        ),
    ]
    budget = QueryBudget(
        max_total_items=2,
        offset=1,
        maximum_total_characters=6,
        max_items_per_source=1,
    )
    result = apply_budget(evidence, budget)
    assert len(result) == 1
    assert result[0].item_id == "b"


@then("the retrieval budget edge cases succeed")
def step_retrieval_budget_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise embedding provider edge cases")
def step_embedding_provider_edge_cases(context) -> None:
    provider = HashEmbeddingProvider(dimensions=4)
    empty_vectors = provider.embed_texts([])
    assert empty_vectors.shape == (0, 4)

    try:
        EmbeddingProviderConfig(provider_id="unknown", dimensions=2).build_provider()
        raise AssertionError("Expected unknown provider to raise")
    except ValueError:
        pass


@then("the embedding provider edge cases succeed")
def step_embedding_provider_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise snapshot reference parsing edge cases")
def step_snapshot_reference_edge_cases(context) -> None:
    for raw in ["invalid", "extractor:"]:
        try:
            parse_extraction_snapshot_reference(raw)
            raise AssertionError("Expected parse error")
        except ValueError:
            pass


@then("the snapshot reference parsing edge cases succeed")
def step_snapshot_reference_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise text extraction edge cases")
def step_text_extraction_edge_cases(context) -> None:
    class DummyResult:
        def __init__(self, *, text: str, last_error: str, messages: list[dict[str, str]]):
            self.done = False
            self.text = text
            self.last_error = last_error
            self.messages = messages

    nested_text = "alpha <span>beta <span>gamma</span></span>"
    messages = [
        {
            "role": "user",
            "content": (
                "Your last edit did not validate.\n"
                "Issues:\n"
                "- nested spans\n\n"
                "Please fix the markup using str_replace.\n"
                "Current text:\n"
                "---\n"
                "alpha beta gamma\n"
                "---"
            ),
        }
    ]
    dummy = DummyResult(text=nested_text, last_error="validation failed", messages=messages)

    original = text_extract_module.run_tool_loop
    try:
        text_extract_module.run_tool_loop = lambda **kwargs: dummy
        request = TextExtractRequest(
            text="alpha beta gamma",
            client=LlmClientConfig(provider="openai", model="gpt-4o-mini", api_key="test"),
            normalize_nested_spans=True,
        )
        result = apply_text_extract(request)
        assert result.warnings
    finally:
        text_extract_module.run_tool_loop = original

    normalized = text_extract_module._normalize_nested_spans("</span>alpha")
    assert normalized.startswith("</span>")


@then("the text extraction edge cases succeed")
def step_text_extraction_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise pipeline configuration edge cases")
def step_pipeline_configuration_edge_cases(context) -> None:
    try:
        PipelineExtractorConfig(stages=[PipelineStageSpec(extractor_id="pipeline")])
        raise AssertionError("Expected pipeline step validation to raise")
    except ValueError:
        pass
    try:
        resolve_extractor("unknown-extractor")
        raise AssertionError("Expected unknown extractor to raise")
    except KeyError:
        pass

    class DummyDoclingConfig:
        retriever = "mlx"

    import sys
    import types

    docling_module = types.ModuleType("docling")
    document_converter = types.ModuleType("docling.document_converter")
    document_converter.DocumentConverter = object
    datamodel = types.ModuleType("docling.datamodel")
    pipeline_options = types.ModuleType("docling.datamodel.pipeline_options")

    class PdfPipelineOptions:
        pass

    pipeline_options.PdfPipelineOptions = PdfPipelineOptions
    datamodel.pipeline_options = pipeline_options
    docling_module.datamodel = datamodel
    docling_module.document_converter = document_converter

    patched_names = [
        "docling",
        "docling.datamodel",
        "docling.datamodel.pipeline_options",
        "docling.document_converter",
    ]
    original_modules = {name: sys.modules.get(name) for name in patched_names}
    sys.modules["docling"] = docling_module
    sys.modules["docling.datamodel"] = datamodel
    sys.modules["docling.datamodel.pipeline_options"] = pipeline_options
    sys.modules["docling.document_converter"] = document_converter

    try:
        parsed = DoclingGraniteExtractor().validate_config({"retriever": "mlx"})
        assert parsed.retriever == "mlx"

        parsed = DoclingSmolExtractor().validate_config({"retriever": "mlx"})
        assert parsed.retriever == "mlx"
    finally:
        for name, original in original_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


@then("the pipeline configuration edge cases succeed")
def step_pipeline_configuration_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise extraction snapshot edge cases")
def step_extraction_snapshot_edge_cases(context) -> None:
    corpus = Corpus.open(_corpus_path(context, "corpus"))
    text_path = _resolve_fixture_path(context, "note.txt")
    binary_path = _resolve_fixture_path(context, "note.bin")
    skipped_path = _resolve_fixture_path(context, "skip.bin")
    text_result = corpus.ingest_item(
        text_path.read_bytes(),
        filename=text_path.name,
        media_type="text/plain",
        source_uri=f"file:{text_path.name}",
    )
    binary_result = corpus.ingest_item(
        binary_path.read_bytes(),
        filename=binary_path.name,
        media_type="application/octet-stream",
        source_uri=f"file:{binary_path.name}",
    )
    skipped_result = corpus.ingest_item(
        skipped_path.read_bytes() if skipped_path.exists() else b"skip",
        filename=skipped_path.name,
        media_type="application/octet-stream",
        source_uri=f"file:{skipped_path.name}",
    )
    unknown_path = context.workdir / "unknown.bin"
    unknown_path.write_bytes(b"unknown")
    unknown_result = corpus.ingest_item(
        unknown_path.read_bytes(),
        filename=unknown_path.name,
        media_type="application/octet-stream",
        source_uri=f"file:{unknown_path.name}",
    )
    missing_text_path = context.workdir / "missing.bin"
    missing_text_path.write_bytes(b"missing")
    missing_text_result = corpus.ingest_item(
        missing_text_path.read_bytes(),
        filename=missing_text_path.name,
        media_type="application/octet-stream",
        source_uri=f"file:{missing_text_path.name}",
    )
    none_text_path = context.workdir / "none.bin"
    none_text_path.write_bytes(b"none")
    none_text_result = corpus.ingest_item(
        none_text_path.read_bytes(),
        filename=none_text_path.name,
        media_type="application/octet-stream",
        source_uri=f"file:{none_text_path.name}",
    )

    config_manifest = create_extraction_configuration_manifest(
        extractor_id="pipeline",
        name="default",
        configuration={"stages": [{"extractor_id": "pass-through-text", "configuration": {}}]},
    )
    manifest = create_extraction_snapshot_manifest(corpus, configuration=config_manifest)
    snapshot_dir = corpus.extraction_snapshot_dir(
        extractor_id="pipeline", snapshot_id=manifest.snapshot_id
    )
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    text_dir = snapshot_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    empty_relpath = f"text/{text_result.item_id}.txt"
    text_dir.joinpath(f"{text_result.item_id}.txt").write_text("", encoding="utf-8")
    binary_relpath = f"text/{binary_result.item_id}.txt"
    text_dir.joinpath(f"{binary_result.item_id}.txt").write_text("converted", encoding="utf-8")

    manifest = manifest.model_copy(
        update={
            "items": [
                ExtractionItemResult(
                    item_id=text_result.item_id,
                    status="extracted",
                    final_text_relpath=empty_relpath,
                ),
                ExtractionItemResult(
                    item_id=binary_result.item_id,
                    status="extracted",
                    final_text_relpath=binary_relpath,
                ),
                ExtractionItemResult(
                    item_id=binary_result.item_id,
                    status="errored",
                    error_type="RuntimeError",
                    error_message="boom",
                ),
                ExtractionItemResult(
                    item_id=skipped_result.item_id,
                    status="skipped",
                ),
                ExtractionItemResult(
                    item_id="missing-item",
                    status="extracted",
                ),
                ExtractionItemResult(
                    item_id=unknown_result.item_id,
                    status="unknown",
                ),
                ExtractionItemResult(
                    item_id=missing_text_result.item_id,
                    status="extracted",
                    final_text_relpath=f"text/{missing_text_result.item_id}.txt",
                ),
                ExtractionItemResult(
                    item_id=none_text_result.item_id,
                    status="extracted",
                    final_text_relpath=None,
                ),
            ]
        }
    )
    write_extraction_snapshot_manifest(snapshot_dir=snapshot_dir, manifest=manifest)

    build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="default",
        configuration={"stages": [{"extractor_id": "pass-through-text", "configuration": {}}]},
    )

    missing_config_manifest = create_extraction_configuration_manifest(
        extractor_id="pipeline",
        name="missing",
        configuration={"stages": [{"extractor_id": "pass-through-text", "configuration": {}}]},
    )
    missing_manifest = create_extraction_snapshot_manifest(
        corpus, configuration=missing_config_manifest
    )
    missing_dir = corpus.extraction_snapshot_dir(
        extractor_id="pipeline", snapshot_id=missing_manifest.snapshot_id
    )
    missing_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = missing_dir / "manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()
    build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="missing",
        configuration={"stages": [{"extractor_id": "pass-through-text", "configuration": {}}]},
    )


@then("the extraction snapshot edge cases succeed")
def step_extraction_snapshot_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise vector retriever helper edge cases")
def step_vector_retriever_edge_cases(context) -> None:
    corpus = Corpus.open(_corpus_path(context, "corpus"))
    text_path = _resolve_fixture_path(context, "note.txt")
    md_path = _resolve_fixture_path(context, "note.md")
    corpus.ingest_item(
        text_path.read_bytes(),
        filename=text_path.name,
        media_type="text/plain",
        source_uri=f"file:{text_path.name}",
    )
    corpus.ingest_item(
        md_path.read_bytes(),
        filename=md_path.name,
        media_type="text/markdown",
        source_uri=f"file:{md_path.name}",
    )

    catalog = corpus.load_catalog()
    items = list(catalog.items.values())
    markdown_item = next(item for item in items if str(getattr(item, "relpath", "")).endswith("note.md"))
    text_item = next(item for item in items if str(getattr(item, "relpath", "")).endswith("note.txt"))

    assert load_tf_text(
        corpus,
        item_id=str(getattr(markdown_item, "id")),
        relpath=str(getattr(markdown_item, "relpath")),
        media_type=str(getattr(markdown_item, "media_type")),
        extraction_reference=None,
    )
    assert load_tf_text(
        corpus,
        item_id=str(getattr(text_item, "id")),
        relpath=str(getattr(text_item, "relpath")),
        media_type=str(getattr(text_item, "media_type")),
        extraction_reference=None,
    )

    assert build_tf_snippet("alpha beta", None, max_chars=None) == "alpha beta"
    assert build_tf_snippet("alpha beta", None, max_chars=0) == ""
    assert build_tf_snippet("alpha beta", (0, 5), max_chars=5)
    assert _find_first_match("alpha", ["zzz"]) is None

    left = {"a": 1.0}
    right = {"a": 1.0, "b": 1.0}
    left_norm = _vector_norm(left)
    right_norm = _vector_norm(right)
    assert _cosine_similarity(left, left_norm=left_norm, right=right, right_norm=right_norm) > 0
    assert _cosine_similarity(right, left_norm=right_norm, right=left, right_norm=left_norm) > 0

    query_tokens = _tokenize_text("gamma")
    query_vector = _term_frequencies(query_tokens)
    query_norm = _vector_norm(query_vector)
    scored = _score_items(
        corpus,
        items,
        query_tokens=query_tokens,
        query_vector=query_vector,
        query_norm=query_norm,
        extraction_reference=None,
        snippet_characters=None,
    )
    assert scored == []

    retriever = TfVectorRetriever()
    snapshot = retriever.build_snapshot(corpus, configuration_name="default", configuration={})
    populated = retriever.query(
        corpus,
        snapshot=snapshot,
        query_text="alpha",
        budget=QueryBudget(max_total_items=5, offset=0, maximum_total_characters=2000, max_items_per_source=5),
    )
    assert populated.evidence
    empty_result = retriever.query(
        corpus,
        snapshot=snapshot,
        query_text="!!!",
        budget=QueryBudget(max_total_items=5, offset=0, maximum_total_characters=2000, max_items_per_source=5),
    )
    assert empty_result.evidence == []

    extraction_dir = corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id="snap")
    extraction_dir.mkdir(parents=True, exist_ok=True)
    text_dir = extraction_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    text_dir.joinpath(f"{text_item.id}.txt").write_text("extracted", encoding="utf-8")
    config_with_snapshot = TfVectorConfiguration(extraction_snapshot="pipeline:snap")
    assert count_tf_text_items(corpus, items, config_with_snapshot) >= 1
    merged = TfVectorConfiguration.model_validate(
        {
            "pipeline": {
                "index": {
                    "extraction_snapshot": "pipeline:snap",
                    "snippet_characters": 42,
                }
            }
        }
    )
    assert merged.extraction_snapshot == "pipeline:snap"
    assert merged.snippet_characters == 42
    non_dict_index = TfVectorConfiguration.model_validate(
        {"pipeline": {"index": "not-a-dict"}}
    )
    assert non_dict_index.pipeline == {"index": "not-a-dict"}
    pre_set = TfVectorConfiguration.model_validate(
        {
            "extraction_snapshot": "pipeline:fixed",
            "snippet_characters": 5,
            "pipeline": {
                "index": {
                    "extraction_snapshot": "pipeline:ignored",
                    "snippet_characters": 99,
                }
            },
        }
    )
    assert pre_set.extraction_snapshot == "pipeline:fixed"
    assert pre_set.snippet_characters == 5

    binary_path = context.workdir / "note.bin"
    binary_path.write_bytes(b"\\x00\\x01")
    corpus.ingest_item(
        binary_path.read_bytes(),
        filename=binary_path.name,
        media_type="application/octet-stream",
        source_uri=f"file:{binary_path.name}",
    )
    binary_item = next(item for item in corpus.load_catalog().items.values() if str(item.relpath).endswith(".bin"))
    assert (
        load_tf_text(
            corpus,
            item_id=str(binary_item.id),
            relpath=str(binary_item.relpath),
            media_type=str(binary_item.media_type),
            extraction_reference=None,
        )
        is None
    )

    config = TfVectorConfiguration(extraction_snapshot="missing:snapshot")
    try:
        resolve_tf_reference(corpus, config)
        raise AssertionError("Expected missing extraction snapshot to raise")
    except FileNotFoundError:
        pass

    scan_config = ScanConfiguration(extraction_snapshot="pipeline:snap")
    assert count_scan_text_items(corpus, items, scan_config) >= 1
    assert load_scan_text(
        corpus,
        item_id=str(getattr(markdown_item, "id")),
        relpath=str(getattr(markdown_item, "relpath")),
        media_type=str(getattr(markdown_item, "media_type")),
        extraction_reference=parse_extraction_snapshot_reference("pipeline:snap"),
    )
    assert find_scan_match("alpha", ["zzz"]) is None
    assert build_scan_snippet("", None, max_chars=5) == ""

    scan_retriever = ScanRetriever()
    scan_snapshot = scan_retriever.build_snapshot(corpus, configuration_name="default", configuration={})
    scan_result = scan_retriever.query(
        corpus,
        snapshot=scan_snapshot,
        query_text="alpha",
        budget=QueryBudget(max_total_items=5, offset=0, maximum_total_characters=2000, max_items_per_source=5),
    )
    assert scan_result.evidence

    try:
        resolve_scan_reference(corpus, ScanConfiguration(extraction_snapshot="missing:snap"))
        raise AssertionError("Expected missing scan snapshot to raise")
    except FileNotFoundError:
        pass


@then("the vector retriever helper edge cases succeed")
def step_vector_retriever_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise embedding index helper edge cases")
def step_embedding_index_helper_edge_cases(context) -> None:
    corpus = Corpus.open(_corpus_path(context, "corpus"))
    text_path = _resolve_fixture_path(context, "note.txt")
    corpus.ingest_item(
        text_path.read_bytes(),
        filename=text_path.name,
        media_type="text/plain",
        source_uri=f"file:{text_path.name}",
    )

    config = EmbeddingIndexConfiguration(
        embedding_provider=EmbeddingProviderConfig(provider_id="hash-embedding", dimensions=2),
        snippet_characters=None,
    )
    assert resolve_extraction_reference(corpus, config) is None
    try:
        resolve_extraction_reference(
            corpus,
            EmbeddingIndexConfiguration(
                embedding_provider=EmbeddingProviderConfig(provider_id="hash-embedding", dimensions=2),
                extraction_snapshot="pipeline:missing",
            ),
        )
        raise AssertionError("Expected missing extraction snapshot to raise")
    except FileNotFoundError:
        pass

    embeddings = np.array([[1.0, 0.0]], dtype=np.float32)
    candidates = _top_indices_batched(embeddings=embeddings, query_vector=embeddings[0], limit=5, batch_rows=1)
    assert candidates == [0]
    assert _top_indices_batched(embeddings=np.array([], dtype=np.float32), query_vector=embeddings[0], limit=1) == []

    assert embedding_candidate_limit(0) == 1

    catalog = corpus.load_catalog()
    item = next(iter(catalog.items.values()))
    record = ChunkRecord(item_id=str(getattr(item, "id")), span_start=0, span_end=5)
    evidence = _build_evidence(
        corpus,
        snapshot=create_snapshot_manifest(
            corpus,
            configuration=create_configuration_manifest(
                retriever_id="embedding-index-file", name="default", configuration=config.model_dump()
            ),
            stats={},
        ),
        configuration=config,
        candidates=[0],
        embeddings=embeddings,
        query_vector=embeddings[0],
        chunk_records=[record],
        extraction_reference=None,
    )
    assert len(evidence) == 1
    assert build_embedding_snippet("alpha beta", (0, 5), None) == _extract_span_text(
        "alpha beta", (0, 5)
    )
    assert build_embedding_snippet("alpha beta", (5, 3), 4) == "alph"

    extraction_dir = corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id="snap")
    extraction_dir.mkdir(parents=True, exist_ok=True)
    text_dir = extraction_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    text_dir.joinpath(f"{item.id}.txt").write_text("extracted", encoding="utf-8")
    extraction_reference = parse_extraction_snapshot_reference("pipeline:snap")
    extracted = load_embedding_text(
        corpus,
        item_id=str(item.id),
        relpath=str(item.relpath),
        media_type=str(item.media_type),
        extraction_reference=extraction_reference,
    )
    assert extracted == "extracted"

    file_retriever = EmbeddingIndexFileRetriever()
    file_snapshot = file_retriever.build_snapshot(
        corpus,
        configuration_name="default",
        configuration=config.model_dump(),
    )
    file_result = file_retriever.query(
        corpus,
        snapshot=file_snapshot,
        query_text="alpha",
        budget=QueryBudget(max_total_items=5, offset=0, maximum_total_characters=2000, max_items_per_source=5),
    )
    assert file_result.evidence

    inmemory = EmbeddingIndexInMemoryRetriever()
    inmemory_snapshot = inmemory.build_snapshot(
        corpus,
        configuration_name="default",
        configuration={
            **config.model_dump(),
            "maximum_cache_total_items": 1,
        },
    )
    inmemory.query(
        corpus,
        snapshot=inmemory_snapshot,
        query_text="alpha",
        budget=QueryBudget(max_total_items=5, offset=0, maximum_total_characters=2000, max_items_per_source=5),
    )
    try:
        corpus.ingest_item(
            b"second item",
            filename="second.txt",
            media_type="text/plain",
            source_uri="file:second.txt",
        )
        inmemory.build_snapshot(
            corpus,
            configuration_name="default",
            configuration={
                **config.model_dump(),
                "maximum_cache_total_items": 1,
            },
        )
        raise AssertionError("Expected maximum_cache_total_items to raise")
    except ValueError:
        pass


@then("the embedding index helper edge cases succeed")
def step_embedding_index_helper_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise sqlite retriever helper edge cases")
def step_sqlite_retriever_helper_edge_cases(context) -> None:
    corpus = Corpus.open(_corpus_path(context, "corpus"))
    text_path = _resolve_fixture_path(context, "note.txt")
    corpus.ingest_item(
        text_path.read_bytes(),
        filename=text_path.name,
        media_type="text/plain",
        source_uri=f"file:{text_path.name}",
    )

    tokens = _tokenize_query("the Alpha")
    assert tokens == ["the", "alpha"]
    stop_words = _resolve_stop_words("english")
    filtered = _apply_stop_words(tokens, stop_words)
    assert "the" not in filtered
    assert "alpha" in filtered
    assert _apply_stop_words(tokens, set()) == tokens
    assert _resolve_stop_words(None) == set()

    assert sqlite_candidate_limit(2) == 10

    config = SqliteFullTextSearchConfiguration()
    try:
        SqliteFullTextSearchConfiguration(stop_words="invalid")
        raise AssertionError("Expected invalid stop_words to raise")
    except ValueError:
        pass
    try:
        SqliteFullTextSearchConfiguration(rerank_enabled=True)
        raise AssertionError("Expected missing rerank_model to raise")
    except ValueError:
        pass
    binary_path = context.workdir / "note.bin"
    binary_path.write_bytes(b"\x00\x01")
    corpus.ingest_item(
        binary_path.read_bytes(),
        filename=binary_path.name,
        media_type="application/octet-stream",
        source_uri=f"file:{binary_path.name}",
    )
    extraction_reference = None
    db_path = corpus.root / "test.sqlite"
    stats = _build_full_text_search_index(
        db_path=db_path,
        corpus=corpus,
        items=corpus.load_catalog().items.values(),
        configuration=config,
        extraction_reference=extraction_reference,
    )
    assert stats["items"] >= 1

    try:
        resolve_sqlite_reference(corpus, SqliteFullTextSearchConfiguration(extraction_snapshot="missing:snap"))
        raise AssertionError("Expected missing extraction snapshot to raise")
    except FileNotFoundError:
        pass

    connection = sqlite3.connect(str(db_path))
    try:
        _ensure_full_text_search_version_five(connection)
        _create_full_text_search_schema(connection)
        connection.execute(
            "INSERT INTO chunks_full_text_search (content, item_id, source_uri, media_type, relpath, title, start_offset, end_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("alpha beta", "item-1", None, "text/plain", "note.txt", None, 0, 5),
        )
        connection.commit()
    finally:
        connection.close()

    evidence = _query_full_text_search_index(db_path, query_text="alpha", limit=5, snippet_characters=10)
    assert evidence

    ranked = _rank_candidates(evidence)
    snapshot = create_snapshot_manifest(
        corpus,
        configuration=create_configuration_manifest(
            retriever_id="sqlite-full-text-search", name="default", configuration=config.model_dump()
        ),
        stats={},
        snapshot_artifacts=[str(db_path.relative_to(corpus.root))],
    )
    budget = QueryBudget(max_total_items=5, offset=0, maximum_total_characters=2000, max_items_per_source=5)
    reranked = _apply_rerank_if_enabled(
        ranked,
        query_tokens=["alpha"],
        snapshot=snapshot,
        budget=budget,
        rerank_enabled=True,
        rerank_top_k=1,
    )
    assert reranked

    no_rerank = _apply_rerank_if_enabled(
        ranked,
        query_tokens=["alpha"],
        snapshot=snapshot,
        budget=budget,
        rerank_enabled=False,
        rerank_top_k=1,
    )
    assert no_rerank

    resolved_path = _resolve_snapshot_db_path(corpus, snapshot)
    assert resolved_path.is_file()

    try:
        _resolve_snapshot_db_path(
            corpus,
            create_snapshot_manifest(
                corpus,
                configuration=create_configuration_manifest(
                    retriever_id="sqlite-full-text-search", name="default", configuration=config.model_dump()
                ),
                stats={},
                snapshot_artifacts=[],
            ),
        )
        raise AssertionError("Expected missing snapshot artifacts to raise")
    except FileNotFoundError:
        pass

    try:
        list(_iter_chunks("alpha", chunk_size=2, chunk_overlap=2))
        raise AssertionError("Expected invalid chunk overlap to raise")
    except ValueError:
        pass


@then("the sqlite retriever helper edge cases succeed")
def step_sqlite_retriever_helper_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise hybrid retriever helper edge cases")
def step_hybrid_retriever_helper_edge_cases(context) -> None:
    try:
        HybridConfiguration(lexical_weight=0.9, embedding_weight=0.05)
        raise AssertionError("Expected invalid weights to raise")
    except ValueError:
        pass

    config = HybridConfiguration()
    _ensure_retriever_supported(config)

    try:
        _ensure_retriever_supported(HybridConfiguration(lexical_retriever="hybrid"))
        raise AssertionError("Expected invalid lexical retriever to raise")
    except ValueError:
        pass

    try:
        _ensure_retriever_supported(HybridConfiguration(embedding_retriever="hybrid"))
        raise AssertionError("Expected invalid embedding retriever to raise")
    except ValueError:
        pass

    budget = QueryBudget(max_total_items=3, offset=1, maximum_total_characters=10, max_items_per_source=2)
    expanded = _expand_component_budget(budget)
    assert expanded.max_total_items > budget.max_total_items
    assert expanded.offset == 0

    lexical = [
        Evidence(
            item_id="a",
            source_uri=None,
            media_type="text/plain",
            score=1.0,
            rank=1,
            text="alpha",
            content_ref=None,
            span_start=None,
            span_end=None,
            stage="lexical",
            configuration_id="",
            snapshot_id="",
            metadata={},
            hash="",
        )
    ]
    embedding: List[Evidence] = []
    fused = _fuse_evidence(lexical, embedding, lexical_weight=0.5, embedding_weight=0.5)
    assert fused[0].stage == "hybrid"

    embedding = [
        Evidence(
            item_id="b",
            source_uri=None,
            media_type="text/plain",
            score=0.4,
            rank=1,
            text="beta",
            content_ref=None,
            span_start=None,
            span_end=None,
            stage="embedding",
            configuration_id="",
            snapshot_id="",
            metadata={},
            hash="",
        )
    ]
    fused = _fuse_evidence(lexical, embedding, lexical_weight=0.7, embedding_weight=0.3)
    assert len(fused) == 2

    corpus = Corpus.init(_corpus_path(context, "hybrid"))
    corpus.ingest_note("alpha beta", title="Doc")
    retriever = HybridRetriever()
    snapshot = retriever.build_snapshot(corpus, configuration_name="default", configuration={})
    result = retriever.query(
        corpus,
        snapshot=snapshot,
        query_text="alpha",
        budget=QueryBudget(max_total_items=5, offset=0, maximum_total_characters=2000, max_items_per_source=5),
    )
    assert result.evidence


@then("the hybrid retriever helper edge cases succeed")
def step_hybrid_retriever_helper_edge_cases_done(context) -> None:
    assert context is not None


@when("I exercise graph extraction edge cases")
def step_graph_extraction_edge_cases(context) -> None:
    short_entities = _extract_entities("Ab", max_words=1, min_length=3)
    assert short_entities == []
    long_entities = _extract_entities("Able", max_words=1, min_length=3)
    assert "Able" in long_entities


@then("the graph extraction edge cases succeed")
def step_graph_extraction_edge_cases_done(context) -> None:
    assert context is not None
