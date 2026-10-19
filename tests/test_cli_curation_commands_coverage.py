from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
import yaml
from pydantic import BaseModel

import biblicus.cli as cli_package
from biblicus.cli import graph as cli_graph
from biblicus.cli import topic_classifier as cli_topic_classifier
from biblicus.corpus import Corpus


class _StubOutput(BaseModel):
    label: str = "stub"
    classifier_id: str = "classifier-a"
    model_version: str = "v1"
    classifier_corpus_uri: str = "file:///authority"
    target_corpus_uri: str = "file:///target"
    summary: Dict[str, Any] = {}
    items: List[Dict[str, Any]] = []
    skipped_items: List[Dict[str, Any]] = []


def _run_cli(capsys: pytest.CaptureFixture[str], argument_list: List[str]) -> Tuple[int, str, str]:
    exit_code = cli_package.main(argument_list)
    captured = capsys.readouterr()
    return exit_code, captured.out, captured.err


def _initialize_corpus(tmp_path: Path) -> Path:
    corpus_path = tmp_path / "corpus"
    Corpus.init(corpus_path)
    return corpus_path


def _write_source_file(tmp_path: Path, name: str = "paper.txt", body: str = "paper body") -> Path:
    source_path = tmp_path / name
    source_path.write_text(body, encoding="utf-8")
    return source_path


def _write_metadata_file(tmp_path: Path, payload: Any) -> Path:
    metadata_path = tmp_path / "metadata.yml"
    metadata_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return metadata_path


def _ingest_with_metadata(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    metadata_payload: Any,
    extra_arguments: List[str] | None = None,
) -> Tuple[int, str, str]:
    corpus_path = _initialize_corpus(tmp_path)
    source_path = _write_source_file(tmp_path)
    metadata_path = _write_metadata_file(tmp_path, metadata_payload)
    return _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "ingest",
            str(source_path),
            "--metadata-file",
            str(metadata_path),
            *(extra_arguments or []),
        ],
    )


def _only_catalog_item(tmp_path: Path) -> Any:
    catalog = Corpus.open(tmp_path / "corpus").load_catalog()
    assert len(catalog.items) == 1
    return next(iter(catalog.items.values()))


def test_ingest_metadata_file_missing_reports_not_found(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A missing metadata file is reported as an ingest metadata file error."""
    corpus_path = _initialize_corpus(tmp_path)
    source_path = _write_source_file(tmp_path)

    exit_code, _, error_output = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "ingest",
            str(source_path),
            "--metadata-file",
            str(tmp_path / "absent.yml"),
        ],
    )

    assert exit_code == 2
    assert "Ingest metadata file not found" in error_output


def test_ingest_metadata_file_with_invalid_yaml_is_rejected(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Metadata files that are not valid YAML are rejected with a clear message."""
    corpus_path = _initialize_corpus(tmp_path)
    source_path = _write_source_file(tmp_path)
    metadata_path = tmp_path / "broken.yml"
    metadata_path.write_text("key: [unclosed", encoding="utf-8")

    exit_code, _, error_output = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "ingest",
            str(source_path),
            "--metadata-file",
            str(metadata_path),
        ],
    )

    assert exit_code == 2
    assert "Invalid ingest metadata file" in error_output


@pytest.mark.parametrize(
    "tags_value, expected_tags",
    [
        ("solo", ["solo"]),
        ("   ", []),
        (["alpha", " ", 7, "beta"], ["alpha", "beta"]),
    ],
)
def test_ingest_metadata_tags_accept_strings_and_lists(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    tags_value: Any,
    expected_tags: List[str],
) -> None:
    """Metadata tags may be a string or a list and blank entries are dropped."""
    exit_code, _, _ = _ingest_with_metadata(capsys, tmp_path, {"tags": tags_value})

    assert exit_code == 0
    assert _only_catalog_item(tmp_path).tags == expected_tags


def test_ingest_metadata_tags_of_wrong_type_are_rejected(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Numeric metadata tags are rejected."""
    exit_code, _, error_output = _ingest_with_metadata(capsys, tmp_path, {"tags": 5})

    assert exit_code == 2
    assert "tags must be a string or list of strings" in error_output


def test_ingest_import_rationale_must_not_be_blank(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A blank import rationale is rejected."""
    exit_code, _, error_output = _ingest_with_metadata(
        capsys, tmp_path, {}, ["--import-rationale", "   "]
    )

    assert exit_code == 2
    assert "Import rationale must not be blank" in error_output


def test_ingest_import_rationale_merges_into_existing_curation(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The import rationale is merged into an existing curation mapping."""
    exit_code, _, _ = _ingest_with_metadata(
        capsys,
        tmp_path,
        {"curation": {"owner": "editor"}},
        ["--import-rationale", " Needed for history "],
    )

    assert exit_code == 0
    assert _only_catalog_item(tmp_path).metadata["curation"] == {
        "owner": "editor",
        "import_rationale": "Needed for history",
    }


def test_ingest_import_rationale_rejects_malformed_curation(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A curation value that is not a mapping cannot receive a rationale."""
    exit_code, _, error_output = _ingest_with_metadata(
        capsys, tmp_path, {"curation": "text"}, ["--import-rationale", "why"]
    )

    assert exit_code == 2
    assert "curation must be a mapping/object" in error_output


def test_ingest_blank_date_flag_is_rejected(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Blank date flags are rejected before ingest."""
    exit_code, _, error_output = _ingest_with_metadata(
        capsys, tmp_path, {}, ["--published-at", "  "]
    )

    assert exit_code == 2
    assert "published_at must not be blank" in error_output


@pytest.mark.parametrize(
    "metadata_payload, expected_message",
    [
        ({"dates": "2020"}, "dates must be a mapping/object"),
        ({"date_provenance": "manual"}, "date_provenance must be a mapping/object"),
        ({"published": "2020"}, "Use dates.published_at"),
    ],
)
def test_ingest_malformed_date_metadata_is_rejected(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    metadata_payload: Dict[str, Any],
    expected_message: str,
) -> None:
    """Malformed or legacy date metadata fails with a specific message."""
    exit_code, _, error_output = _ingest_with_metadata(capsys, tmp_path, metadata_payload)

    assert exit_code == 2
    assert expected_message in error_output


def test_ingest_drops_empty_dates_and_provenance_blocks(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Empty dates and date provenance mappings are not stored with the item."""
    exit_code, _, _ = _ingest_with_metadata(capsys, tmp_path, {"dates": {}, "date_provenance": {}})

    item = _only_catalog_item(tmp_path)
    assert exit_code == 0
    assert "dates" not in item.metadata
    assert "date_provenance" not in item.metadata


def test_ingest_media_type_from_metadata_file_is_used(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A media type declared in the metadata file overrides guessing."""
    exit_code, _, _ = _ingest_with_metadata(capsys, tmp_path, {"media_type": " text/markdown "})

    assert exit_code == 0
    assert _only_catalog_item(tmp_path).media_type == "text/markdown"


def test_ingest_blank_metadata_media_type_falls_back_to_guess(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A blank metadata media type leaves media type guessing in charge."""
    exit_code, _, _ = _ingest_with_metadata(capsys, tmp_path, {"media_type": "  "})

    assert exit_code == 0
    assert _only_catalog_item(tmp_path).media_type == "text/plain"


def test_standard_ingest_rejects_remote_source_path(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Standard metadata ingest only accepts local file paths."""
    corpus_path = _initialize_corpus(tmp_path)

    exit_code, _, error_output = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "ingest",
            "https://example.test/paper.pdf",
            "--source-uri",
            "urn:test:paper",
        ],
    )

    assert exit_code == 2
    assert "requires a local file path" in error_output


def test_standard_ingest_rejects_missing_local_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Standard metadata ingest reports a missing local source file."""
    corpus_path = _initialize_corpus(tmp_path)

    exit_code, _, error_output = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "ingest",
            str(tmp_path / "absent.pdf"),
            "--source-uri",
            "urn:test:absent",
        ],
    )

    assert exit_code == 2
    assert "Ingest source file not found" in error_output


def test_standard_ingest_rejects_notes_and_multiple_files(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Standard metadata ingest refuses notes and more than one file."""
    corpus_path = _initialize_corpus(tmp_path)
    first = _write_source_file(tmp_path, "first.txt", "first")
    second = _write_source_file(tmp_path, "second.txt", "second")

    note_code, _, note_error = _run_cli(
        capsys,
        ["--corpus", str(corpus_path), "ingest", "--note", "hello", "--source-uri", "urn:x"],
    )
    many_code, _, many_error = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "ingest",
            str(first),
            str(second),
            "--source-uri",
            "urn:y",
        ],
    )

    assert note_code == 2
    assert "requires a local file path" in note_error
    assert many_code == 2
    assert "requires exactly one local file path" in many_error


def test_corpus_audit_reports_missing_extraction_snapshot(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Auditing against a missing extraction snapshot fails with exit code 2."""
    corpus_path = _initialize_corpus(tmp_path)

    exit_code, _, error_output = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "corpus",
            "audit",
            "--extraction-snapshot",
            "pipeline:missing-snapshot",
        ],
    )

    assert exit_code == 2
    assert error_output.startswith("Corpus audit failed:")


def test_corpus_audit_markdown_and_json_formats(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The audit command prints Markdown or JSON depending on the format flag."""
    corpus_path = _initialize_corpus(tmp_path)

    markdown_code, markdown_output, _ = _run_cli(
        capsys, ["--corpus", str(corpus_path), "corpus", "audit", "--format", "markdown"]
    )
    json_code, json_output, _ = _run_cli(
        capsys, ["--corpus", str(corpus_path), "corpus", "audit", "--format", "json"]
    )

    assert markdown_code == 0
    assert markdown_output.startswith("# Corpus Audit")
    assert json_code == 0
    assert json.loads(json_output)["summary"]["item_count"] == 0


def test_build_loads_configuration_files(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Build composes configuration files before building a retrieval snapshot."""
    corpus_path = _initialize_corpus(tmp_path)
    configuration_path = tmp_path / "retrieval.yml"
    configuration_path.write_text("{}\n", encoding="utf-8")

    exit_code, output, _ = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "build",
            "--retriever",
            "scan",
            "--configuration",
            str(configuration_path),
        ],
    )

    assert exit_code == 0
    assert json.loads(output)["configuration"]["retriever_id"] == "scan"


def test_graph_extract_rejects_negative_retry_attempts(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Graph extraction rejects negative retry attempts before building."""
    corpus_path = _initialize_corpus(tmp_path)

    exit_code, _, error_output = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "graph",
            "extract",
            "--extractor",
            "ner-entities",
            "--extraction-snapshot",
            "pipeline:snapshot-1",
            "--item-retry-attempts",
            "-1",
        ],
    )

    assert exit_code == 2
    assert "item_retry_attempts: Input should be greater than or equal to 0" in error_output


def test_graph_extract_progress_reports_heartbeat_and_errors(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Graph progress callbacks render heartbeat and errored item events."""
    cli_graph._graph_extract_progress(
        "heartbeat",
        {"snapshot_id": "s1", "item_index": 2, "nodes": 4, "edges": 5},
    )
    cli_graph._graph_extract_progress(
        "processed",
        {
            "item_index": 1,
            "items_total": 2,
            "item_id": "i1",
            "status": "errored",
            "nodes": 0,
            "edges": 0,
            "error_message": "boom",
            "error_reason": "timeout",
        },
    )
    cli_graph._graph_extract_progress("unknown-event", {})
    error_output = capsys.readouterr().err

    assert "[graph] heartbeat snapshot=s1 itemIndex=2 nodes=4 edges=5" in error_output
    assert "status=errored" in error_output
    assert "error=boom reason=timeout" in error_output


def test_graph_export_prints_payload_and_writes_output_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Graph export prints to standard output or writes to the requested file."""
    corpus_path = _initialize_corpus(tmp_path)
    seen_snapshots: List[Any] = []

    def fake_export(corpus: Corpus, *, snapshot: Any) -> _StubOutput:
        seen_snapshots.append(snapshot)
        return _StubOutput(label="graph-export")

    monkeypatch.setattr("biblicus.graph.extraction.export_graph_snapshot", fake_export)
    output_path = tmp_path / "export.json"

    printed_code, printed_output, _ = _run_cli(
        capsys,
        ["--corpus", str(corpus_path), "graph", "export", "--snapshot", "ner:snap-1"],
    )
    written_code, written_output, _ = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "graph",
            "export",
            "--snapshot",
            "ner:snap-1",
            "--output",
            str(output_path),
        ],
    )

    assert printed_code == 0
    assert json.loads(printed_output)["label"] == "graph-export"
    assert written_code == 0
    assert written_output == ""
    assert json.loads(output_path.read_text(encoding="utf-8"))["label"] == "graph-export"
    assert seen_snapshots[0].extractor_id == "ner"
    assert seen_snapshots[0].snapshot_id == "snap-1"


def test_ontology_apply_forwards_snapshot_identifiers(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ontology apply passes taxonomy, relationship and graph snapshot identifiers."""
    corpus_path = _initialize_corpus(tmp_path)
    received: Dict[str, Any] = {}

    def fake_apply(**keywords: Any) -> _StubOutput:
        received.update(keywords)
        return _StubOutput(label="applied")

    monkeypatch.setattr("biblicus.ontology.apply_ontology_to_graph", fake_apply)

    exit_code, output, _ = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "ontology",
            "apply",
            "--taxonomy",
            "latest",
            "--relationships",
            "rel-1",
            "--graph-snapshot",
            "ner:snap-1",
        ],
    )

    assert exit_code == 0
    assert json.loads(output)["label"] == "applied"
    assert received["taxonomy_snapshot_id"] == "latest"
    assert received["ontology_snapshot_id"] == "rel-1"
    assert received["graph_snapshot"] == "ner:snap-1"


def test_context_pack_build_blocks_reads_request_from_standard_input(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Build-blocks builds a context pack from a block request on standard input."""
    request = {
        "blocks": [
            {"block_id": "doctrine-1", "section": "doctrine", "text": "mission", "required": True},
            {"block_id": "memory-1", "section": "memory", "text": "recent note"},
        ],
        "max_tokens": 50,
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request)))

    exit_code, output, _ = _run_cli(capsys, ["context-pack", "build-blocks"])
    payload = json.loads(output)

    assert exit_code == 0
    assert [block["block_id"] for block in payload["included_blocks"]] == [
        "doctrine-1",
        "memory-1",
    ]


def test_context_pack_build_blocks_requires_standard_input(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Build-blocks rejects an empty standard input."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("  \n"))

    exit_code, _, error_output = _run_cli(capsys, ["context-pack", "build-blocks"])

    assert exit_code == 2
    assert "Context block build requires" in error_output


def test_topic_granularity_sweep_prints_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Topic granularity sweep prints the sweep output as JSON by default."""
    corpus_path = _initialize_corpus(tmp_path)
    configuration_path = tmp_path / "topics.yml"
    configuration_path.write_text("{}\n", encoding="utf-8")
    received: Dict[str, Any] = {}

    def fake_sweep(**keywords: Any) -> _StubOutput:
        received.update(keywords)
        return _StubOutput(label="sweep")

    monkeypatch.setattr("biblicus.topic_granularity.run_topic_granularity_sweep", fake_sweep)

    exit_code, output, _ = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "analyze",
            "topic-granularity-sweep",
            "--configuration",
            str(configuration_path),
            "--extraction-snapshot",
            "pipeline:snap-1",
            "--target-topic-range",
            "5:8",
        ],
    )

    assert exit_code == 0
    assert json.loads(output)["label"] == "sweep"
    assert received["target_topic_range"] == "5:8"
    assert received["extraction_snapshot"].snapshot_id == "snap-1"


def test_topic_context_prints_json_and_markdown(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Topic context prints JSON or Markdown depending on the format."""
    corpus_path = _initialize_corpus(tmp_path)
    received: Dict[str, Any] = {}

    def fake_context(**keywords: Any) -> _StubOutput:
        received.update(keywords)
        return _StubOutput(label="context")

    monkeypatch.setattr("biblicus.topic_context.build_topic_context", fake_context)
    monkeypatch.setattr(
        "biblicus.topic_context.topic_context_markdown",
        lambda output: f"# Context {output.label}",
    )
    base_arguments = [
        "--corpus",
        str(corpus_path),
        "analyze",
        "topic-context",
        "--topic-modeling-snapshot",
        "topics-1",
        "--include-outlier",
    ]

    json_code, json_output, _ = _run_cli(capsys, [*base_arguments, "--format", "json"])
    markdown_code, markdown_output, _ = _run_cli(capsys, [*base_arguments, "--format", "markdown"])

    assert json_code == 0
    assert json.loads(json_output)["label"] == "context"
    assert markdown_code == 0
    assert markdown_output.strip() == "# Context context"
    assert received["include_outlier"] is True
    assert received["topic_modeling_snapshot_id"] == "topics-1"


def test_topic_classifier_ingest_classify_forwards_tags_and_flags(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ingest-classify merges tags and forwards classification options."""
    corpus_path = _initialize_corpus(tmp_path)
    received: Dict[str, Any] = {}

    def fake_ingest_and_classify(**keywords: Any) -> _StubOutput:
        received.update(keywords)
        return _StubOutput(label="classified")

    monkeypatch.setattr(
        "biblicus.topic_classifier.ingest_and_classify_topic_classifier_item",
        fake_ingest_and_classify,
    )

    exit_code, output, _ = _run_cli(
        capsys,
        [
            "--corpus",
            str(corpus_path),
            "topic-classifier",
            "ingest-classify",
            "--classifier",
            "history",
            "--tags",
            "a,b",
            "--tag",
            "b",
            "--tag",
            "c",
            "--record",
            "--top-k",
            "3",
            "https://example.test/paper",
        ],
    )

    assert exit_code == 0
    assert json.loads(output)["label"] == "classified"
    assert received["tags"] == ["a", "b", "c"]
    assert received["classifier_id"] == "history"
    assert received["source"] == "https://example.test/paper"
    assert received["top_k"] == 3
    assert received["record"] is True


def test_topic_classifier_review_batch_renders_markdown_table(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review-batch renders a Markdown table with scores, keywords and decisions."""
    corpus_path = _initialize_corpus(tmp_path)
    review = _StubOutput(
        classifier_id="history",
        model_version="v7",
        summary={"candidate_items": 2, "review_recommended_items": 1},
        items=[
            {
                "item_id": "item-1",
                "title": "Pipes | and\nlines",
                "proposed_topic_uid": "topic-a",
                "classifier_topic_uid": None,
                "classifier_score": 0.5,
                "review_recommended": True,
                "unsupervised_topic_id": 4,
                "unsupervised_keywords": [{"keyword": "alpha"}, {"keyword": "beta"}],
                "reviewer_decision": None,
            },
            {
                "item_id": "item-2",
                "title": None,
                "proposed_topic_uid": None,
                "classifier_topic_uid": "topic-b",
                "classifier_score": None,
                "review_recommended": False,
                "unsupervised_topic_id": None,
                "reviewer_decision": "accepted",
            },
        ],
    )
    monkeypatch.setattr(
        "biblicus.topic_classifier.build_topic_classifier_batch_review",
        lambda **keywords: review,
    )
    arguments = [
        "--corpus",
        str(corpus_path),
        "topic-classifier",
        "review-batch",
        "--classifier",
        "history",
        "--extraction-snapshot",
        "pipeline:snap-1",
        "--topic-modeling-snapshot",
        "topics-1",
    ]

    markdown_code, markdown_output, _ = _run_cli(capsys, [*arguments, "--format", "markdown"])
    json_code, json_output, _ = _run_cli(capsys, arguments)

    assert markdown_code == 0
    assert "# Topic Classifier Batch Review: history" in markdown_output
    assert "- Candidate items: 2" in markdown_output
    assert (
        "| item-1 | Pipes \\| and lines | topic-a | discovered | 0.500 | true | 4 | alpha, beta | pending |"
        in markdown_output
    )
    assert "| item-2 |  |  | topic-b |  | false |  |  | accepted |" in markdown_output
    assert json_code == 0
    assert json.loads(json_output)["model_version"] == "v7"


def test_topic_classifier_project_renders_markdown_with_skipped_items(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project renders projected and skipped items as Markdown tables."""
    classifier_corpus = tmp_path / "authority"
    target_corpus = tmp_path / "target"
    Corpus.init(classifier_corpus)
    Corpus.init(target_corpus)
    projection = _StubOutput(
        classifier_id="history",
        model_version="v2",
        summary={"projected_items": 1, "skipped_items": 1, "review_recommended_items": 0},
        items=[
            {
                "item_id": "item-1",
                "title": "Projected",
                "topic_uid": None,
                "score": 0.25,
                "review_recommended": False,
                "topic_candidates": [
                    {"topic_uid": "topic-a", "score": 0.75},
                    {"topic_uid": None, "score": None},
                    "not-a-candidate",
                ],
                "source_uri": "urn:test:one",
            }
        ],
        skipped_items=[{"item_id": "item-2", "title": None, "reason": "no text"}],
    )
    monkeypatch.setattr(
        "biblicus.topic_classifier.project_topic_classifier_items", lambda **keywords: projection
    )
    arguments = [
        "topic-classifier",
        "project",
        "--classifier-corpus",
        str(classifier_corpus),
        "--target-corpus",
        str(target_corpus),
        "--classifier",
        "history",
        "--extraction-snapshot",
        "pipeline:snap-1",
        "--all",
    ]

    markdown_code, markdown_output, _ = _run_cli(capsys, [*arguments, "--format", "markdown"])
    json_code, json_output, _ = _run_cli(capsys, arguments)

    assert markdown_code == 0
    assert "# Topic Classifier Projection: history" in markdown_output
    assert (
        "| item-1 | Projected | review | 0.250 | false | topic-a 0.750; discovered | urn:test:one |"
        in markdown_output
    )
    assert "## Skipped Items" in markdown_output
    assert "| item-2 |  | no text |" in markdown_output
    assert json_code == 0
    assert json.loads(json_output)["classifier_id"] == "history"


def test_topic_classifier_candidates_markdown_ignores_non_list_input() -> None:
    """Candidate rendering returns nothing for non-list input and skips non-mappings."""
    assert cli_topic_classifier._topic_classifier_candidates_markdown(None) == ""
    assert cli_topic_classifier._topic_classifier_candidates_markdown(["x", {"topic_uid": "t"}]) == "t"


def test_topic_classifier_projection_markdown_without_skipped_items() -> None:
    """Projection Markdown omits the skipped section when nothing was skipped."""
    markdown = cli_topic_classifier._topic_classifier_projection_markdown(
        {
            "classifier_id": "history",
            "model_version": "v1",
            "classifier_corpus_uri": "file:///a",
            "target_corpus_uri": "file:///b",
            "summary": {"projected_items": 0, "skipped_items": 0, "review_recommended_items": 0},
            "items": [],
        }
    )

    assert "## Skipped Items" not in markdown
    assert "- Projected items: 0" in markdown


def test_research_intake_pending_renders_markdown(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pending intake items print as Markdown or JSON depending on the format."""
    corpus_path = _initialize_corpus(tmp_path)
    monkeypatch.setattr(
        "biblicus.research_intake.list_pending_research_intake_items",
        lambda corpus: _StubOutput(label="pending"),
    )
    monkeypatch.setattr(
        "biblicus.research_intake.research_intake_pending_markdown",
        lambda output: f"# Pending {output.label}",
    )
    arguments = ["--corpus", str(corpus_path), "research-intake", "pending"]

    markdown_code, markdown_output, _ = _run_cli(capsys, [*arguments, "--format", "markdown"])
    json_code, json_output, _ = _run_cli(capsys, arguments)

    assert markdown_code == 0
    assert markdown_output.strip() == "# Pending pending"
    assert json_code == 0
    assert json.loads(json_output)["label"] == "pending"
