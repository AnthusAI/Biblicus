from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import biblicus.research_intake as research_intake_module
from biblicus.corpus import Corpus
from biblicus.research_intake import (
    ACCEPTED_STATUS,
    PENDING_REVIEW_STATUS,
    REJECTED_STATUS,
    ResearchIntakeConfiguration,
    ResearchIntakePendingOutput,
    _validate_candidate_metadata,
    _validate_local_source_path,
    assess_research_intake_candidate,
    decide_research_intake,
    decide_research_intake_item,
    ingest_research_intake_candidate,
    list_pending_research_intake_items,
    metadata_text,
    nearest_corpus_evidence,
    research_intake_pending_markdown,
)
from biblicus.topic_classifier import TopicClassifierPrediction


def _prediction(
    *, score: float | None, topic_uid: str | None = "agents"
) -> TopicClassifierPrediction:
    return TopicClassifierPrediction(
        classifier_id="classifier",
        item_id="candidate",
        model_version="model",
        bertopic_topic_id=0,
        topic_uid=topic_uid,
        display_name="Agents" if topic_uid else None,
        score=score,
        review_recommended=False,
        representative_evidence={},
        recorded=False,
    )


def test_research_intake_configuration_rejects_duplicate_fields() -> None:
    """Reject duplicate metadata field paths."""
    with pytest.raises(ValidationError, match="duplicate"):
        ResearchIntakeConfiguration.model_validate(
            {
                "schema_version": 1,
                "required_fields": ["title", "title"],
                "metadata_text_fields": ["title", "abstract"],
            }
        )


def test_research_intake_metadata_text_uses_configured_fields() -> None:
    """Build assessment text from title and abstract only."""
    text = metadata_text(
        metadata={
            "title": "Agent Paper",
            "abstract": "Agent memory planning.",
            "tags": ["leaked-topic"],
        },
        fields=["title", "abstract"],
    )

    assert text == "Agent Paper\nAgent memory planning."
    assert "leaked-topic" not in text


def test_research_intake_metadata_text_formats_structured_values() -> None:
    """Format configured list, mapping, scalar, and missing field values."""
    text = metadata_text(
        metadata={
            "title": ["Agent", "Memory"],
            "details": {"signals": {"score": 1}},
            "year": 2026,
        },
        fields=["title", "details.signals", "year", "details.signals.score.value"],
    )

    assert text == 'Agent, Memory\n{"score": 1}\n2026'


def test_research_intake_metadata_requires_abstract() -> None:
    """Require official candidate assessment fields."""
    config = ResearchIntakeConfiguration()

    with pytest.raises(ValueError, match="abstract"):
        _validate_candidate_metadata(metadata={"title": "Only Title"}, configuration=config)


def test_research_intake_requires_non_empty_assessment_text() -> None:
    """Reject configuration text fields that produce no assessment payload."""
    config = ResearchIntakeConfiguration(
        required_fields=[],
        metadata_text_fields=["missing"],
    )

    with pytest.raises(ValueError, match="empty assessment text"):
        _validate_candidate_metadata(metadata={"title": "Only Title"}, configuration=config)


def test_research_intake_validates_source_path(tmp_path: Path) -> None:
    """Require a real local file path for pre-ingest assessment."""
    with pytest.raises(ValueError, match="local file path"):
        _validate_local_source_path(Path("https://example.test/paper.pdf"))

    with pytest.raises(FileNotFoundError, match="not found"):
        _validate_local_source_path(tmp_path / "missing.pdf")


def test_research_intake_decision_thresholds() -> None:
    """Classify candidates into accepted, rejected, and pending decisions."""
    config = ResearchIntakeConfiguration()

    accepted, _ = decide_research_intake(
        prediction=_prediction(score=0.8),
        corpus_similarity=0.2,
        configuration=config,
    )
    rejected, _ = decide_research_intake(
        prediction=_prediction(score=0.1),
        corpus_similarity=0.0,
        configuration=config,
    )
    pending, _ = decide_research_intake(
        prediction=_prediction(score=0.4),
        corpus_similarity=0.0,
        configuration=config,
    )

    assert accepted == ACCEPTED_STATUS
    assert rejected == REJECTED_STATUS
    assert pending == PENDING_REVIEW_STATUS


def test_assess_research_intake_candidate_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Assess candidate metadata without mutating the corpus catalog."""
    corpus = Corpus.init(tmp_path / "corpus")
    corpus.ingest_item(
        b"agent memory planning",
        filename="accepted.txt",
        media_type="text/plain",
        title="Accepted Agent",
        metadata={"abstract": "agent memory planning"},
        source_uri="urn:test:accepted",
    )
    source_path = tmp_path / "candidate.txt"
    source_path.write_text("candidate bytes", encoding="utf-8")
    before_count = len(corpus.load_catalog().items)

    monkeypatch.setattr(
        research_intake_module,
        "classify_topic_classifier_text",
        lambda **_kwargs: _prediction(score=0.9),
    )

    output = assess_research_intake_candidate(
        corpus=corpus,
        classifier_id="classifier",
        source_path=source_path,
        metadata={"title": "Candidate Agent", "abstract": "agent memory planning"},
        configuration=ResearchIntakeConfiguration(),
    )

    assert output.decision == ACCEPTED_STATUS
    assert output.item_id is None
    assert len(corpus.load_catalog().items) == before_count


def test_ingest_research_intake_candidate_stores_accepted_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accepted intake stores the item with curation metadata and provenance."""
    corpus = Corpus.init(tmp_path / "corpus")
    corpus.ingest_item(
        b"agent memory planning",
        filename="accepted.txt",
        media_type="text/plain",
        title="Accepted Agent",
        metadata={"abstract": "agent memory planning"},
        source_uri="urn:test:accepted",
    )
    source_path = tmp_path / "candidate.bin"
    source_path.write_bytes(b"candidate bytes")

    monkeypatch.setattr(
        research_intake_module,
        "classify_topic_classifier_text",
        lambda **_kwargs: _prediction(score=0.9),
    )

    output = ingest_research_intake_candidate(
        corpus=corpus,
        classifier_id="classifier",
        source_path=source_path,
        metadata={
            "title": "Candidate Agent",
            "abstract": "agent memory planning",
            "tags": "candidate",
        },
        configuration=ResearchIntakeConfiguration(),
        source_uri="urn:test:candidate",
        media_type="application/x-test",
        tags=["candidate", "cli"],
    )
    item = corpus.get_item(output.item_id or "")

    assert output.decision == ACCEPTED_STATUS
    assert item.source_uri == "urn:test:candidate"
    assert item.media_type == "application/x-test"
    assert item.tags == ["candidate", "cli"]
    assert item.metadata["curation"]["intake_status"] == ACCEPTED_STATUS
    assert item.metadata["curation"]["intake_assessment"]["classifier_score"] == 0.9


def test_ingest_research_intake_candidate_rejects_without_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rejected intake returns JSON-style output and leaves the corpus unchanged."""
    corpus = Corpus.init(tmp_path / "corpus")
    source_path = tmp_path / "candidate.txt"
    source_path.write_text("candidate bytes", encoding="utf-8")

    monkeypatch.setattr(
        research_intake_module,
        "classify_topic_classifier_text",
        lambda **_kwargs: _prediction(score=None, topic_uid=None),
    )

    output = ingest_research_intake_candidate(
        corpus=corpus,
        classifier_id="classifier",
        source_path=source_path,
        metadata={"title": "Candidate Agent", "abstract": "agent memory planning"},
        configuration=ResearchIntakeConfiguration(),
        source_uri=None,
        media_type=None,
        tags=[],
    )

    assert output.decision == REJECTED_STATUS
    assert output.item_id is None
    assert corpus.load_catalog().items == {}


def test_nearest_corpus_evidence_excludes_pending_and_rejected(tmp_path: Path) -> None:
    """Similarity evidence ignores pending and rejected intake statuses."""
    corpus = Corpus.init(tmp_path / "corpus")
    corpus.ingest_item(
        b"agent memory",
        filename="accepted.txt",
        media_type="text/plain",
        title="Accepted Agent",
        metadata={"abstract": "agent memory planning"},
        source_uri="urn:test:accepted",
    )
    corpus.ingest_item(
        b"pending agent memory",
        filename="pending.txt",
        media_type="text/plain",
        title="Pending Agent",
        metadata={"curation": {"intake_status": PENDING_REVIEW_STATUS}},
        source_uri="urn:test:pending",
    )
    corpus.ingest_item(
        b"rejected agent memory",
        filename="rejected.txt",
        media_type="text/plain",
        title="Rejected Agent",
        metadata={"curation": {"intake_status": REJECTED_STATUS}},
        source_uri="urn:test:rejected",
    )

    nearest = nearest_corpus_evidence(
        corpus=corpus,
        candidate_text="agent memory planning",
        limit=3,
    )

    assert [item_id for item_id, _score in nearest] == [
        item.id for item in corpus.load_catalog().items.values() if item.title == "Accepted Agent"
    ]


def test_research_intake_pending_markdown_renders_empty_and_table(tmp_path: Path) -> None:
    """Render pending review output as deterministic Markdown."""
    corpus = Corpus.init(tmp_path / "corpus")
    corpus.ingest_item(
        b"agent memory",
        filename="pending.txt",
        media_type="text/plain",
        title="Pending | Agent",
        metadata={
            "curation": {
                "intake_status": PENDING_REVIEW_STATUS,
                "intake_assessment": {
                    "topic_uid": "agents",
                    "display_name": "Agent | Memory",
                    "classifier_score": 0.4,
                    "corpus_similarity": 0.125,
                },
            }
        },
        source_uri="urn:test:pending",
    )

    empty = research_intake_pending_markdown(
        ResearchIntakePendingOutput(
            corpus_path=str(corpus.root),
            generated_at="2026-05-15T00:00:00Z",
            items=[],
        )
    )
    markdown = research_intake_pending_markdown(list_pending_research_intake_items(corpus=corpus))

    assert "No pending review items." in empty
    assert "Pending \\| Agent" in markdown
    assert "Agent \\| Memory" in markdown
    assert "0.400" in markdown
    assert "0.125" in markdown


def test_decide_research_intake_item_updates_sidecar_metadata(tmp_path: Path) -> None:
    """Human decisions update item curation metadata and reindex the catalog."""
    corpus = Corpus.init(tmp_path / "corpus")
    result = corpus.ingest_item(
        b"agent memory",
        filename="pending.txt",
        media_type="text/plain",
        title="Pending Agent",
        metadata={
            "curation": {
                "intake_status": PENDING_REVIEW_STATUS,
                "intake_assessment": {
                    "classifier_id": "classifier",
                    "model_version": "model",
                    "bertopic_topic_id": 0,
                    "corpus_similarity": 0.4,
                },
            }
        },
        source_uri="urn:test:pending",
    )

    output = decide_research_intake_item(
        corpus=corpus,
        item_id=result.item_id,
        decision="accept",
        topic_uid="agents",
    )
    item = corpus.get_item(result.item_id)

    assert output.decision == ACCEPTED_STATUS
    assert item.metadata["curation"]["intake_status"] == ACCEPTED_STATUS
    assert item.metadata["curation"]["reviewed_topic_uid"] == "agents"


def test_decide_research_intake_item_rejects_markdown_item(tmp_path: Path) -> None:
    """Human decisions update Markdown front matter as the mutable sidecar."""
    corpus = Corpus.init(tmp_path / "corpus")
    result = corpus.ingest_item(
        b"---\n"
        b"title: Pending Agent\n"
        b"curation:\n"
        b"  intake_status: pending_review\n"
        b"  intake_assessment:\n"
        b"    classifier_id: classifier\n"
        b"    model_version: model\n"
        b"    bertopic_topic_id: 0\n"
        b"    reason: Needs review\n"
        b"    nearest_evidence_item_ids:\n"
        b"      - seed\n"
        b"---\n"
        b"# Pending Agent\n",
        filename="pending.md",
        media_type="text/markdown",
        title="Pending Agent",
        metadata={
            "curation": {
                "intake_status": PENDING_REVIEW_STATUS,
                "intake_assessment": {
                    "classifier_id": "classifier",
                    "model_version": "model",
                    "bertopic_topic_id": 0,
                    "reason": "Needs review",
                    "nearest_evidence_item_ids": ["seed"],
                },
            }
        },
        source_uri="urn:test:pending-md",
    )

    output = decide_research_intake_item(
        corpus=corpus,
        item_id=result.item_id,
        decision="reject",
        topic_uid=None,
    )
    item = corpus.get_item(result.item_id)

    assert output.decision == REJECTED_STATUS
    assert output.review_recommended is True
    assert output.nearest_evidence_item_ids == ["seed"]
    assert item.metadata["curation"]["intake_status"] == REJECTED_STATUS


def test_decide_research_intake_item_rejects_invalid_human_decision(tmp_path: Path) -> None:
    """Reject unsupported human decision values."""
    corpus = Corpus.init(tmp_path / "corpus")
    result = corpus.ingest_item(
        b"agent memory",
        filename="pending.txt",
        media_type="text/plain",
        title="Pending Agent",
        metadata={"curation": {"intake_status": PENDING_REVIEW_STATUS}},
        source_uri="urn:test:pending",
    )

    with pytest.raises(ValueError, match="accept or reject"):
        decide_research_intake_item(
            corpus=corpus,
            item_id=result.item_id,
            decision="maybe",
            topic_uid=None,
        )
