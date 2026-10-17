from __future__ import annotations

import json
import sys
import threading
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest
from pydantic import ValidationError

from biblicus import topic_classifier
from biblicus.analysis.models import (
    TopicModelingConfiguration,
    TopicModelingLlmExtractionMethod,
    TopicModelingRepresentationModelConfig,
)
from biblicus.analysis.topic_modeling import TopicModelingDocument
from biblicus.models import ExtractionSnapshotReference
from biblicus.topic_classifier import (
    TopicClassifierProjectionItem,
    TopicClassifierSeedManifest,
    TopicClassifierTopic,
    build_topic_classifier_batch_review,
    classify_topic_classifier_item,
    classify_topic_classifier_text,
    draft_topic_classifier_manifest,
    ingest_and_classify_topic_classifier_item,
    load_topic_classifier_seed_manifest,
    project_topic_classifier_items,
    train_topic_classifier,
)

EXTRACTION_SNAPSHOT = ExtractionSnapshotReference(extractor_id="pipeline", snapshot_id="snap-one")

ITEM_TEXTS_BY_ID: Dict[str, str] = {
    "item-alpha": "alpha agent planning",
    "item-beta": "beta speech recognition",
    "item-gamma": "gamma agent tooling",
    "item-delta": "delta speech decoding",
    "item-orphan": "orphan unrelated words",
}


def _build_manifest_payload() -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "classifier_id": "lab",
        "display_name": "Lab",
        "description": "Lab classifier.",
        "topics": [
            {
                "topic_uid": "agents",
                "display_name": "Agents",
                "description": "Agent systems.",
                "seed_item_ids": ["item-alpha"],
                "holdout_item_ids": ["item-gamma"],
            },
            {
                "topic_uid": "speech",
                "display_name": "Speech",
                "description": "Speech recognition.",
                "seed_item_ids": ["item-beta"],
                "holdout_item_ids": ["item-delta"],
            },
        ],
        "unlabeled_policy": "use_minus_one",
    }


def _write_manifest(path: Path, payload: Optional[Dict[str, Any]] = None) -> Path:
    path.write_text(json.dumps(payload or _build_manifest_payload()), encoding="utf-8")
    return path


def _build_catalog_item(
    item_id: str,
    *,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    created_at: str = "2026-01-01T00:00:00Z",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=item_id,
        title=f"Title {item_id}",
        source_uri=f"file:///{item_id}.txt",
        tags=tags or [],
        metadata=metadata or {},
        created_at=created_at,
    )


class _FakeCorpus:
    def __init__(
        self,
        root: Path,
        *,
        texts_by_item_id: Optional[Dict[str, Optional[str]]] = None,
        items: Optional[List[SimpleNamespace]] = None,
        order: Optional[List[str]] = None,
    ) -> None:
        self.root = root
        self.analysis_dir = root / "analysis"
        self.meta_dir = root / ".biblicus"
        self.texts_by_item_id = texts_by_item_id if texts_by_item_id is not None else {}
        catalog_items = items if items is not None else []
        self.catalog = SimpleNamespace(
            items={item.id: item for item in catalog_items},
            order=order if order is not None else [item.id for item in catalog_items],
            generated_at="2026-01-02T00:00:00Z",
            corpus_uri=f"file://{root}",
        )
        self.snapshots_read: List[str] = []
        self.snapshots_checked: List[str] = []
        self.ingested_sources: List[str] = []
        self.reindex_count = 0

    def load_catalog(self) -> SimpleNamespace:
        return self.catalog

    def analysis_run_dir(self, *, analysis_id: str, snapshot_id: str) -> Path:
        return self.analysis_dir / analysis_id / snapshot_id

    def read_extracted_text(
        self, *, extractor_id: str, snapshot_id: str, item_id: str
    ) -> Optional[str]:
        self.snapshots_read.append(snapshot_id)
        return self.texts_by_item_id.get(item_id)

    def load_extraction_snapshot_manifest(self, *, extractor_id: str, snapshot_id: str):
        self.snapshots_checked.append(snapshot_id)
        return SimpleNamespace(
            configuration=SimpleNamespace(
                extractor_id=extractor_id, name="pipeline-config", configuration={"steps": []}
            )
        )

    def ingest_source(self, source: str, *, tags: Any, allow_external: bool) -> SimpleNamespace:
        self.ingested_sources.append(source)
        return SimpleNamespace(item_id="item-alpha")

    def reindex(self) -> None:
        self.reindex_count += 1


class _FakeBertopicModel:
    constructor_keyword_arguments: Dict[str, Any] = {}
    supports_approximation = True

    def __init__(self, **keyword_arguments: Any) -> None:
        _FakeBertopicModel.constructor_keyword_arguments = keyword_arguments

    @staticmethod
    def topic_for_text(text: str) -> int:
        if "agent" in text:
            return 0
        if "speech" in text:
            return 1
        return 7

    def fit_transform(self, texts: List[str], y: List[int]):
        assignments = [
            label if label >= 0 else self.topic_for_text(text) for text, label in zip(texts, y)
        ]
        probabilities = [{assignment: 0.9} for assignment in assignments]
        return assignments, probabilities

    def get_topic(self, topic_id: int):
        if topic_id == 7:
            return None
        return [(f"keyword{topic_id}", 0.5)]

    def save(self, path: str) -> None:
        Path(path).write_text("fake-model", encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "_FakeBertopicModel":
        assert Path(path).read_text(encoding="utf-8") == "fake-model"
        return cls()

    def transform(self, texts: List[str]):
        topic_id = self.topic_for_text(texts[0])
        return [topic_id], [{topic_id: 0.9}]

    def approximate_distribution(self, texts: List[str]):
        distribution = {0: 0.2, 1: 0.2, 7: 0.1}
        distribution[min(self.topic_for_text(texts[0]), 1)] = 0.7
        return [distribution], None


@pytest.fixture
def fake_bertopic_module(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Install a fake bertopic module for the duration of a test."""
    module = types.ModuleType("bertopic")
    module.BERTopic = _FakeBertopicModel
    module.__biblicus_fake__ = True
    _FakeBertopicModel.constructor_keyword_arguments = {}
    monkeypatch.setitem(sys.modules, "bertopic", module)
    return module


def _build_stage_report(output_documents: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        output_documents=output_documents,
        model_dump=lambda mode="json": {"output_documents": output_documents},
    )


def _build_topic_modeling_documents() -> List[TopicModelingDocument]:
    return [
        TopicModelingDocument(document_id=item_id, source_item_id=item_id, text=text)
        for item_id, text in ITEM_TEXTS_BY_ID.items()
    ]


def _build_training_corpus(root: Path) -> _FakeCorpus:
    return _FakeCorpus(
        root,
        texts_by_item_id=dict(ITEM_TEXTS_BY_ID),
        items=[_build_catalog_item(item_id) for item_id in ITEM_TEXTS_BY_ID],
    )


def _run_training(
    monkeypatch: pytest.MonkeyPatch,
    corpus: _FakeCorpus,
    manifest_path: Path,
    configuration: Optional[Dict[str, object]] = None,
):
    monkeypatch.setattr(
        topic_classifier,
        "_collect_documents",
        lambda **_: (_build_topic_modeling_documents(), _build_stage_report()),
    )
    return train_topic_classifier(
        corpus=corpus,
        manifest_path=manifest_path,
        configuration_name="baseline",
        configuration=configuration or {},
        extraction_snapshot=EXTRACTION_SNAPSHOT,
    )


@pytest.fixture
def trained_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_bertopic_module: types.ModuleType
) -> _FakeCorpus:
    """Train a classifier with the fake BERTopic module and return its corpus."""
    corpus = _build_training_corpus(tmp_path / "corpus")
    manifest_path = _write_manifest(tmp_path / "manifest.json")
    _run_training(monkeypatch, corpus, manifest_path)
    return corpus


def test_topic_requires_nonblank_text_fields() -> None:
    """Reject whitespace-only topic text and strip surrounding whitespace."""
    payload = _build_manifest_payload()["topics"][0]
    payload["display_name"] = "   "

    with pytest.raises(ValidationError, match="value must not be empty"):
        TopicClassifierTopic.model_validate(payload)

    payload["display_name"] = "  Agents  "
    assert TopicClassifierTopic.model_validate(payload).display_name == "Agents"


def test_topic_rejects_non_text_topic_uid() -> None:
    """Pass non-string topic text through to type validation."""
    payload = _build_manifest_payload()["topics"][0]
    payload["topic_uid"] = 12

    with pytest.raises(ValidationError, match="valid string"):
        TopicClassifierTopic.model_validate(payload)


def test_topic_rejects_blank_item_identifier() -> None:
    """Reject empty seed item identifiers."""
    payload = _build_manifest_payload()["topics"][0]
    payload["seed_item_ids"] = ["  "]

    with pytest.raises(ValidationError, match="item identifiers must not be empty"):
        TopicClassifierTopic.model_validate(payload)


def test_topic_rejects_duplicate_item_identifiers() -> None:
    """Reject repeated identifiers inside one seed list."""
    payload = _build_manifest_payload()["topics"][0]
    payload["seed_item_ids"] = ["item-alpha", "item-alpha"]

    with pytest.raises(ValidationError, match="Duplicate item identifiers: item-alpha"):
        TopicClassifierTopic.model_validate(payload)


def test_topic_rejects_item_that_is_both_seed_and_holdout() -> None:
    """Reject an item listed as seed and holdout within a topic."""
    payload = _build_manifest_payload()["topics"][0]
    payload["holdout_item_ids"] = ["item-alpha"]

    with pytest.raises(ValidationError, match="Item cannot be both seed and holdout"):
        TopicClassifierTopic.model_validate(payload)


def test_manifest_requires_nonblank_text_fields() -> None:
    """Reject whitespace-only manifest text and strip valid text."""
    payload = _build_manifest_payload()
    payload["classifier_id"] = " "

    with pytest.raises(ValidationError, match="value must not be empty"):
        TopicClassifierSeedManifest.model_validate(payload)

    payload["classifier_id"] = " lab "
    assert TopicClassifierSeedManifest.model_validate(payload).classifier_id == "lab"


def test_manifest_rejects_non_text_classifier_id() -> None:
    """Pass non-string manifest text through to type validation."""
    payload = _build_manifest_payload()
    payload["classifier_id"] = 5

    with pytest.raises(ValidationError, match="valid string"):
        TopicClassifierSeedManifest.model_validate(payload)


def test_manifest_rejects_unsupported_schema_version() -> None:
    """Reject manifests declaring an unknown schema version."""
    payload = _build_manifest_payload()
    payload["schema_version"] = 999

    with pytest.raises(ValidationError, match="Unsupported topic classifier schema version"):
        TopicClassifierSeedManifest.model_validate(payload)


def test_manifest_rejects_unknown_unlabeled_policy() -> None:
    """Reject unlabeled policies other than use_minus_one."""
    payload = _build_manifest_payload()
    payload["unlabeled_policy"] = "drop"

    with pytest.raises(ValidationError, match="unlabeled_policy must be 'use_minus_one'"):
        TopicClassifierSeedManifest.model_validate(payload)


def test_manifest_rejects_holdout_reused_across_topics() -> None:
    """Reject holdout items assigned to more than one topic."""
    payload = _build_manifest_payload()
    payload["topics"][1]["holdout_item_ids"] = ["item-gamma"]

    with pytest.raises(ValidationError, match="Holdout item item-gamma is reused in topics"):
        TopicClassifierSeedManifest.model_validate(payload)


def test_load_manifest_returns_validated_manifest(tmp_path: Path) -> None:
    """Load a valid manifest file into the strict model."""
    manifest = load_topic_classifier_seed_manifest(_write_manifest(tmp_path / "manifest.json"))

    assert manifest.classifier_id == "lab"
    assert [topic.topic_uid for topic in manifest.topics] == ["agents", "speech"]


def test_load_manifest_reports_invalid_json(tmp_path: Path) -> None:
    """Convert malformed JSON into a clear value error."""
    path = tmp_path / "manifest.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid topic classifier manifest JSON"):
        load_topic_classifier_seed_manifest(path)


def test_load_manifest_reports_validation_failure(tmp_path: Path) -> None:
    """Convert schema violations into a clear value error."""
    path = _write_manifest(tmp_path / "manifest.json", {"classifier_id": "lab"})

    with pytest.raises(ValueError, match="Invalid topic classifier manifest:"):
        load_topic_classifier_seed_manifest(path)


def test_draft_manifest_applies_overrides_and_appends_topic(tmp_path: Path) -> None:
    """Draft a manifest with replaced identity fields and one extra topic."""
    base_path = _write_manifest(tmp_path / "base.json")
    output_path = tmp_path / "nested" / "draft.json"

    output = draft_topic_classifier_manifest(
        base_manifest_path=base_path,
        output_path=output_path,
        classifier_id="lab-draft",
        display_name="Lab Draft",
        description="Draft description.",
        topic_uid="vision",
        topic_display_name="Vision",
        topic_description="Computer vision.",
        seed_item_ids=["item-orphan"],
        holdout_item_ids=[],
    )

    drafted = json.loads(output_path.read_text(encoding="utf-8"))
    assert output.classifier_id == "lab-draft"
    assert output.topic_count == 3
    assert output.added_topic_uid == "vision"
    assert drafted["display_name"] == "Lab Draft"
    assert drafted["description"] == "Draft description."
    assert drafted["topics"][-1]["topic_uid"] == "vision"


def test_draft_manifest_keeps_base_identity_without_overrides(tmp_path: Path) -> None:
    """Draft a manifest that preserves the base identity fields."""
    base_path = _write_manifest(tmp_path / "base.json")
    output_path = tmp_path / "draft.json"

    output = draft_topic_classifier_manifest(
        base_manifest_path=base_path,
        output_path=output_path,
        classifier_id=None,
        display_name=None,
        description=None,
        topic_uid="vision",
        topic_display_name="Vision",
        topic_description="Computer vision.",
        seed_item_ids=["item-orphan"],
        holdout_item_ids=[],
    )

    drafted = json.loads(output_path.read_text(encoding="utf-8"))
    assert output.classifier_id == "lab"
    assert drafted["display_name"] == "Lab"
    assert drafted["description"] == "Lab classifier."


def test_classifier_configuration_rejects_non_single_llm_extraction() -> None:
    """Reject LLM extraction methods other than single."""
    base = TopicModelingConfiguration.model_validate({})
    configuration = base.model_copy(
        update={
            "llm_extraction": base.llm_extraction.model_copy(
                update={"enabled": True, "method": TopicModelingLlmExtractionMethod.ITEMIZE}
            )
        }
    )

    with pytest.raises(ValueError, match="requires llm_extraction.method to be 'single'"):
        topic_classifier._validate_classifier_configuration(configuration)


def test_classifier_configuration_rejects_representation_model() -> None:
    """Reject BERTopic representation models during classifier training."""
    base = TopicModelingConfiguration.model_validate({})
    configuration = base.model_copy(
        update={
            "bertopic_analysis": base.bertopic_analysis.model_copy(
                update={"representation_model": TopicModelingRepresentationModelConfig()}
            )
        }
    )

    with pytest.raises(ValueError, match="does not support representation_model"):
        topic_classifier._validate_classifier_configuration(configuration)


def test_classifier_configuration_accepts_defaults() -> None:
    """Accept the default configuration without raising."""
    topic_classifier._validate_classifier_configuration(
        TopicModelingConfiguration.model_validate({})
    )


def test_manifest_document_validation_reports_missing_extracted_text() -> None:
    """Report manifest items that have no extracted document."""
    manifest = TopicClassifierSeedManifest.model_validate(_build_manifest_payload())
    documents = _build_topic_modeling_documents()[:2]

    with pytest.raises(ValueError, match="extracted text for manifest item IDs: item-delta"):
        topic_classifier._validate_manifest_documents(manifest, documents)


def test_training_labels_mark_unseeded_documents_as_unlabeled() -> None:
    """Label seed documents by topic order and others as unlabeled."""
    manifest = TopicClassifierSeedManifest.model_validate(_build_manifest_payload())

    labels = topic_classifier._training_labels_for_documents(
        manifest, _build_topic_modeling_documents()
    )

    assert labels == [0, 1, -1, -1, -1]


def test_fit_requires_bertopic_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explain how to install BERTopic when it cannot be imported."""
    monkeypatch.setitem(sys.modules, "bertopic", None)

    with pytest.raises(ValueError, match="Topic classifier training requires BERTopic"):
        topic_classifier._fit_bertopic_classifier(
            documents=[], labels=[], config=TopicModelingConfiguration().bertopic_analysis
        )


def test_fit_requires_bertopic_class(monkeypatch: pytest.MonkeyPatch) -> None:
    """Treat a bertopic module without a BERTopic class as unavailable."""
    monkeypatch.setitem(sys.modules, "bertopic", types.ModuleType("bertopic"))

    with pytest.raises(ValueError, match="Topic classifier training requires BERTopic"):
        topic_classifier._fit_bertopic_classifier(
            documents=[], labels=[], config=TopicModelingConfiguration().bertopic_analysis
        )


def _build_vectorizer_configuration():
    return TopicModelingConfiguration.model_validate(
        {"bertopic_analysis": {"vectorizer": {"ngram_range": [1, 2], "stop_words": "english"}}}
    ).bertopic_analysis


def test_fit_uses_no_vectorizer_for_fake_bertopic(
    fake_bertopic_module: types.ModuleType,
) -> None:
    """Pass a null vectorizer model when the fake BERTopic module is installed."""
    topic_classifier._fit_bertopic_classifier(
        documents=_build_topic_modeling_documents(),
        labels=[0, 1, -1, -1, -1],
        config=_build_vectorizer_configuration(),
    )

    assert _FakeBertopicModel.constructor_keyword_arguments == {"vectorizer_model": None}


def test_fit_builds_count_vectorizer_for_real_bertopic_module(
    fake_bertopic_module: types.ModuleType,
) -> None:
    """Build a scikit-learn count vectorizer from the vectorizer configuration."""
    fake_bertopic_module.__biblicus_fake__ = False

    topic_classifier._fit_bertopic_classifier(
        documents=_build_topic_modeling_documents(),
        labels=[0, 1, -1, -1, -1],
        config=_build_vectorizer_configuration(),
    )

    vectorizer = _FakeBertopicModel.constructor_keyword_arguments["vectorizer_model"]
    assert vectorizer.ngram_range == (1, 2)
    assert vectorizer.stop_words == "english"


def test_fit_requires_scikit_learn_for_vectorizer(
    monkeypatch: pytest.MonkeyPatch, fake_bertopic_module: types.ModuleType
) -> None:
    """Explain how to install scikit-learn when the vectorizer cannot be built."""
    fake_bertopic_module.__biblicus_fake__ = False
    monkeypatch.setitem(sys.modules, "sklearn.feature_extraction.text", None)

    with pytest.raises(ValueError, match="Vectorizer configuration requires scikit-learn"):
        topic_classifier._fit_bertopic_classifier(
            documents=_build_topic_modeling_documents(),
            labels=[0, 1, -1, -1, -1],
            config=_build_vectorizer_configuration(),
        )


def test_fit_keeps_explicit_vectorizer_model_parameter(
    fake_bertopic_module: types.ModuleType,
) -> None:
    """Respect a vectorizer model supplied through BERTopic parameters."""
    configuration = TopicModelingConfiguration.model_validate(
        {
            "bertopic_analysis": {
                "parameters": {"vectorizer_model": "custom"},
                "vectorizer": {"ngram_range": [1, 1]},
            }
        }
    ).bertopic_analysis

    topic_classifier._fit_bertopic_classifier(
        documents=_build_topic_modeling_documents(),
        labels=[0, 1, -1, -1, -1],
        config=configuration,
    )

    assert _FakeBertopicModel.constructor_keyword_arguments == {"vectorizer_model": "custom"}


def test_fit_reports_topics_and_falls_back_to_numbered_label(
    fake_bertopic_module: types.ModuleType,
) -> None:
    """Build topic records with keyword labels and numbered fallbacks."""
    _, assignments, _, report, topics = topic_classifier._fit_bertopic_classifier(
        documents=_build_topic_modeling_documents(),
        labels=[0, 1, -1, -1, -1],
        config=TopicModelingConfiguration().bertopic_analysis,
    )

    labels_by_topic_id = {topic.topic_id: topic.label for topic in topics}
    assert assignments == [0, 1, 0, 1, 7]
    assert labels_by_topic_id == {0: "keyword0", 1: "keyword1", 7: "Topic 7"}
    assert report.topic_count == 3
    assert report.document_count == 5


def test_fit_prints_heartbeat_while_fitting(
    monkeypatch: pytest.MonkeyPatch,
    fake_bertopic_module: types.ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Emit a progress heartbeat to standard error during long fits."""

    class HeartbeatEvent:
        def __init__(self) -> None:
            self.wait_count = 0
            self.flag = False

        def wait(self, timeout: float) -> bool:
            self.wait_count += 1
            return self.wait_count > 1

        def set(self) -> None:
            self.flag = True

    monkeypatch.setattr(
        topic_classifier,
        "threading",
        SimpleNamespace(Event=HeartbeatEvent, Thread=threading.Thread),
    )

    topic_classifier._fit_bertopic_classifier(
        documents=_build_topic_modeling_documents(),
        labels=[0, 1, -1, -1, -1],
        config=TopicModelingConfiguration().bertopic_analysis,
    )

    assert "bertopic fit_transform elapsed=" in capsys.readouterr().err


def test_train_writes_model_artifacts_and_latest_pointer(
    tmp_path: Path, trained_corpus: _FakeCorpus
) -> None:
    """Persist the model manifest, topic map, holdout evaluation and latest pointer."""
    latest = json.loads(
        (trained_corpus.analysis_dir / "topic-classifier" / "lab-latest.json").read_text()
    )
    run_dir = trained_corpus.analysis_dir / "topic-classifier" / latest["model_version"]
    model_manifest = json.loads((run_dir / "model-manifest.json").read_text())
    topic_map = json.loads((run_dir / "topic-map.json").read_text())
    holdout = json.loads((run_dir / "holdout-evaluation.json").read_text())

    assert (run_dir / "model" / "bertopic").read_text() == "fake-model"
    assert "entity_removal.jsonl" not in model_manifest["artifact_paths"]
    assert model_manifest["stats"]["seed_items"] == 2
    assert model_manifest["stats"]["holdout_items"] == 2
    assert [mapping["topic_uid"] for mapping in topic_map["mappings"]] == ["agents", "speech"]
    assert [entry["bertopic_topic_id"] for entry in topic_map["discovered"]] == [7]
    assert holdout["summary"]["matched_items"] == 2
    assert holdout["summary"]["review_recommended_items"] == 0


def test_train_returns_output_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_bertopic_module: types.ModuleType
) -> None:
    """Return paths and statistics describing the trained model version."""
    corpus = _build_training_corpus(tmp_path / "corpus")

    output = _run_training(monkeypatch, corpus, _write_manifest(tmp_path / "manifest.json"))

    assert output.classifier_id == "lab"
    assert Path(output.model_manifest_path).is_file()
    assert Path(output.latest_pointer_path).name == "lab-latest.json"
    assert output.stats == {
        "documents": 5,
        "seed_items": 2,
        "holdout_items": 2,
        "mapped_topics": 2,
        "discovered_topics": 1,
    }


def test_train_lists_entity_removal_cache_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_bertopic_module: types.ModuleType
) -> None:
    """Record the entity removal cache artifact when entity removal is enabled."""
    corpus = _build_training_corpus(tmp_path / "corpus")
    monkeypatch.setattr(
        topic_classifier,
        "_apply_entity_removal",
        lambda *, documents, config, cache_path: (_build_stage_report(len(documents)), documents),
    )

    output = _run_training(
        monkeypatch,
        corpus,
        _write_manifest(tmp_path / "manifest.json"),
        {"entity_removal": {"enabled": True, "provider": "spacy"}},
    )

    model_manifest = json.loads(Path(output.model_manifest_path).read_text())
    assert "entity_removal.jsonl" in model_manifest["artifact_paths"]


def test_train_rejects_manifest_with_unknown_catalog_items(
    tmp_path: Path, fake_bertopic_module: types.ModuleType
) -> None:
    """Fail before fitting when the manifest names items missing from the catalog."""
    corpus = _FakeCorpus(tmp_path / "corpus", items=[_build_catalog_item("item-alpha")])

    with pytest.raises(ValueError, match="references unknown item IDs"):
        train_topic_classifier(
            corpus=corpus,
            manifest_path=_write_manifest(tmp_path / "manifest.json"),
            configuration_name="baseline",
            configuration={},
            extraction_snapshot=EXTRACTION_SNAPSHOT,
        )


def test_holdout_evaluation_flags_unmapped_topics_for_review() -> None:
    """Recommend review for holdout items assigned to unmapped topics."""
    manifest = TopicClassifierSeedManifest.model_validate(_build_manifest_payload())
    documents = _build_topic_modeling_documents()
    assignments = [0, 1, 7, 1, 7]
    topic_map = {"mappings": [{"bertopic_topic_id": 1, "topic_uid": "speech"}]}

    evaluation = topic_classifier._build_holdout_evaluation(
        classifier_id="lab",
        model_version="v1",
        manifest=manifest,
        documents=documents,
        assignments=assignments,
        probabilities=None,
        topic_map=topic_map,
    )

    by_item = {entry["item_id"]: entry for entry in evaluation["items"]}
    assert by_item["item-gamma"]["predicted_topic_uid"] is None
    assert by_item["item-gamma"]["review_recommended"] is True
    assert by_item["item-gamma"]["score"] is None
    assert by_item["item-delta"]["matched"] is True
    assert evaluation["summary"]["matched_items"] == 1
    assert evaluation["summary"]["review_recommended_items"] == 1


def test_topic_map_keeps_unlisted_topic_without_record_as_discovered() -> None:
    """Build discovered entries with empty keywords when no topic record exists."""
    manifest = TopicClassifierSeedManifest.model_validate(_build_manifest_payload())

    topic_map = topic_classifier._build_topic_map(
        classifier_id="lab",
        model_version="v1",
        manifest=manifest,
        documents=_build_topic_modeling_documents(),
        assignments=[0, 0, 7, 7, 7],
        topics=[],
    )

    assert topic_map["mappings"][0]["topic_uid"] == "agents"
    assert topic_map["mappings"][0]["seed_vote_counts"] == {"agents": 1, "speech": 1}
    assert topic_map["mappings"][0]["keywords"] == []
    assert topic_map["discovered"][0]["keywords"] == []
    assert topic_map["topics"][1]["bertopic_topic_ids"] == []


def test_save_model_requires_save_support(tmp_path: Path) -> None:
    """Reject BERTopic objects that cannot be saved."""
    with pytest.raises(ValueError, match="does not support save"):
        topic_classifier._save_bertopic_model(topic_model=object(), model_path=tmp_path / "model")


def test_load_model_requires_bertopic_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Explain how to install BERTopic when loading a model."""
    monkeypatch.setitem(sys.modules, "bertopic", None)

    with pytest.raises(ValueError, match="classification requires BERTopic"):
        topic_classifier._load_bertopic_model(tmp_path)


def test_load_model_requires_bertopic_class(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Treat a bertopic module without a BERTopic class as unavailable when loading."""
    monkeypatch.setitem(sys.modules, "bertopic", types.ModuleType("bertopic"))

    with pytest.raises(ValueError, match="classification requires BERTopic"):
        topic_classifier._load_bertopic_model(tmp_path)


def test_load_model_requires_load_support(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Reject BERTopic classes that cannot load persisted models."""
    module = types.ModuleType("bertopic")
    module.BERTopic = type("NoLoadBertopic", (), {})
    monkeypatch.setitem(sys.modules, "bertopic", module)

    with pytest.raises(ValueError, match="BERTopic class does not support load"):
        topic_classifier._load_bertopic_model(tmp_path)


def test_model_bundle_requires_latest_pointer(tmp_path: Path) -> None:
    """Report a missing latest pointer for an untrained classifier."""
    corpus = _FakeCorpus(tmp_path)

    with pytest.raises(FileNotFoundError, match="Missing topic classifier latest pointer"):
        topic_classifier._load_model_bundle(corpus=corpus, classifier_id="lab")


def test_model_bundle_requires_model_manifest(tmp_path: Path) -> None:
    """Report a missing model manifest behind the latest pointer."""
    corpus = _FakeCorpus(tmp_path)
    pointer_path = corpus.analysis_dir / "topic-classifier" / "lab-latest.json"
    pointer_path.parent.mkdir(parents=True)
    pointer_path.write_text(json.dumps({"model_version": "v1"}), encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Missing topic classifier model manifest"):
        topic_classifier._load_model_bundle(corpus=corpus, classifier_id="lab")


def test_model_bundle_requires_topic_map(tmp_path: Path) -> None:
    """Report a missing topic map behind the latest pointer."""
    corpus = _FakeCorpus(tmp_path)
    pointer_path = corpus.analysis_dir / "topic-classifier" / "lab-latest.json"
    pointer_path.parent.mkdir(parents=True)
    pointer_path.write_text(json.dumps({"model_version": "v1"}), encoding="utf-8")
    run_dir = corpus.analysis_dir / "topic-classifier" / "v1"
    run_dir.mkdir()
    (run_dir / "model-manifest.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Missing topic classifier topic map"):
        topic_classifier._load_model_bundle(corpus=corpus, classifier_id="lab")


def test_classify_text_returns_ranked_mapped_candidates(trained_corpus: _FakeCorpus) -> None:
    """Rank mapped topic candidates and choose the top one when confident."""
    prediction = classify_topic_classifier_text(
        corpus=trained_corpus,
        classifier_id="lab",
        text="  an agent walks into a room  ",
        item_id="adhoc",
    )

    assert prediction.item_id == "adhoc"
    assert prediction.topic_uid == "agents"
    assert prediction.display_name == "Agents"
    assert prediction.score == pytest.approx(0.7)
    assert prediction.review_recommended is False
    assert [candidate.topic_uid for candidate in prediction.topic_candidates] == [
        "agents",
        "speech",
    ]
    assert [candidate.rank for candidate in prediction.topic_candidates] == [1, 2]
    assert prediction.recorded is False


def test_classify_text_recommends_review_below_threshold(trained_corpus: _FakeCorpus) -> None:
    """Withhold the topic identity when the top score is below the threshold."""
    prediction = classify_topic_classifier_text(
        corpus=trained_corpus,
        classifier_id="lab",
        text="an agent",
        item_id="adhoc",
        review_threshold=0.9,
    )

    assert prediction.topic_uid is None
    assert prediction.display_name is None
    assert prediction.review_recommended is True
    assert prediction.topic_candidates[0].topic_uid == "agents"


def test_classify_text_rejects_non_positive_top_k(trained_corpus: _FakeCorpus) -> None:
    """Reject a top_k below one."""
    with pytest.raises(ValueError, match="top_k must be at least 1"):
        classify_topic_classifier_text(
            corpus=trained_corpus,
            classifier_id="lab",
            text="an agent",
            item_id="adhoc",
            top_k=0,
        )


def test_classify_text_rejects_model_without_approximate_distribution(
    trained_corpus: _FakeCorpus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject models that cannot produce ranked topic candidates."""
    monkeypatch.setattr(_FakeBertopicModel, "approximate_distribution", None)

    with pytest.raises(ValueError, match="must support approximate_distribution"):
        classify_topic_classifier_text(
            corpus=trained_corpus,
            classifier_id="lab",
            text="an agent",
            item_id="adhoc",
        )


def test_classify_text_rejects_empty_text(trained_corpus: _FakeCorpus) -> None:
    """Reject blank classification text."""
    with pytest.raises(ValueError, match="Extracted text for item adhoc is empty"):
        classify_topic_classifier_text(
            corpus=trained_corpus, classifier_id="lab", text="   ", item_id="adhoc"
        )


def test_classify_item_uses_manifest_snapshot_and_reads_text(trained_corpus: _FakeCorpus) -> None:
    """Classify a catalog item using the snapshot recorded in the model manifest."""
    prediction = classify_topic_classifier_item(
        corpus=trained_corpus, classifier_id="lab", item_id="item-beta"
    )

    assert prediction.item_id == "item-beta"
    assert prediction.topic_uid == "speech"
    assert trained_corpus.snapshots_read == ["snap-one"]


def test_classify_item_records_prediction_when_requested(trained_corpus: _FakeCorpus) -> None:
    """Append an audit record and mark the prediction as recorded."""
    first = classify_topic_classifier_item(
        corpus=trained_corpus, classifier_id="lab", item_id="item-beta", record=True
    )
    classify_topic_classifier_item(
        corpus=trained_corpus, classifier_id="lab", item_id="item-alpha", record=True
    )

    records_path = trained_corpus.meta_dir / "topic-classifiers" / "lab" / "predictions.jsonl"
    records = [json.loads(line) for line in records_path.read_text().splitlines()]
    assert first.recorded is True
    assert [record["item_id"] for record in records] == ["item-beta", "item-alpha"]
    assert records[0]["recorded"] is False
    assert "recorded_at" in records[0]


def test_classify_item_rejects_missing_extracted_text(trained_corpus: _FakeCorpus) -> None:
    """Report items that have no extracted text in the snapshot."""
    trained_corpus.texts_by_item_id["item-beta"] = None

    with pytest.raises(ValueError, match="Missing extracted text for item item-beta"):
        classify_topic_classifier_item(
            corpus=trained_corpus, classifier_id="lab", item_id="item-beta"
        )


def test_ingest_and_classify_rebuilds_extraction_snapshot(
    trained_corpus: _FakeCorpus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ingest a source, rebuild extraction artifacts and classify with the new snapshot."""
    build_calls: List[Dict[str, Any]] = []

    def fake_load_or_build(corpus: Any, **keyword_arguments: Any) -> SimpleNamespace:
        build_calls.append(keyword_arguments)
        return SimpleNamespace(snapshot_id="snap-two")

    monkeypatch.setattr(topic_classifier, "load_or_build_extraction_snapshot", fake_load_or_build)

    prediction = ingest_and_classify_topic_classifier_item(
        corpus=trained_corpus,
        classifier_id="lab",
        source="/tmp/new-document.txt",
        tags=["fresh"],
        record=True,
    )

    assert trained_corpus.ingested_sources == ["/tmp/new-document.txt"]
    assert trained_corpus.reindex_count == 1
    assert trained_corpus.snapshots_read == ["snap-two"]
    assert build_calls == [
        {
            "extractor_id": "pipeline",
            "configuration_name": "pipeline-config",
            "configuration": {"steps": []},
            "max_workers": 1,
        }
    ]
    assert prediction.item_id == "item-alpha"
    assert prediction.recorded is True


def _build_projection_pair(tmp_path: Path, trained_corpus: _FakeCorpus) -> _FakeCorpus:
    return _FakeCorpus(
        tmp_path / "target",
        texts_by_item_id={
            "item-alpha": "alpha agent planning",
            "item-beta": None,
            "item-gamma": "   ",
            "item-delta": "delta speech decoding",
        },
        items=[
            _build_catalog_item("item-alpha"),
            _build_catalog_item("item-beta"),
            _build_catalog_item("item-gamma"),
            _build_catalog_item("item-delta"),
        ],
    )


def test_projection_requires_exactly_one_selector(
    tmp_path: Path, trained_corpus: _FakeCorpus
) -> None:
    """Reject projection requests with both or neither selectors."""
    target = _build_projection_pair(tmp_path, trained_corpus)
    arguments = {
        "classifier_corpus": trained_corpus,
        "target_corpus": target,
        "classifier_id": "lab",
        "extraction_snapshot": EXTRACTION_SNAPSHOT,
    }

    with pytest.raises(ValueError, match="requires exactly one of --all or --item-id"):
        project_topic_classifier_items(**arguments)
    with pytest.raises(ValueError, match="requires exactly one of --all or --item-id"):
        project_topic_classifier_items(project_all=True, item_ids=["item-alpha"], **arguments)
    with pytest.raises(ValueError, match="requires exactly one of --all or --item-id"):
        project_topic_classifier_items(item_ids=["  "], **arguments)


def test_projection_all_skips_ineligible_items_and_records(
    tmp_path: Path, trained_corpus: _FakeCorpus
) -> None:
    """Project every item, skip items without usable text and persist audit rows."""
    target = _build_projection_pair(tmp_path, trained_corpus)

    output = project_topic_classifier_items(
        classifier_corpus=trained_corpus,
        target_corpus=target,
        classifier_id="lab",
        extraction_snapshot=EXTRACTION_SNAPSHOT,
        project_all=True,
        record=True,
    )

    records_path = target.meta_dir / "topic-classifiers" / "lab" / "predictions.jsonl"
    records = [json.loads(line) for line in records_path.read_text().splitlines()]
    assert target.snapshots_checked == ["snap-one"]
    assert [item.item_id for item in output.items] == ["item-alpha", "item-delta"]
    assert [item.topic_uid for item in output.items] == ["agents", "speech"]
    assert all(item.recorded for item in output.items)
    assert [skipped.item_id for skipped in output.skipped_items] == ["item-beta", "item-gamma"]
    assert "Missing extracted text" in output.skipped_items[0].reason
    assert "is empty" in output.skipped_items[1].reason
    assert output.summary["projected_items"] == 2
    assert output.summary["skipped_items"] == 2
    assert output.summary["mapped_items"] == 2
    assert output.recorded is True
    assert [record["item_id"] for record in records] == ["item-alpha", "item-delta"]
    assert records[0]["target_corpus_uri"] == target.catalog.corpus_uri


def test_projection_by_item_id_does_not_record_by_default(
    tmp_path: Path, trained_corpus: _FakeCorpus
) -> None:
    """Project only the named item and write no audit rows."""
    target = _build_projection_pair(tmp_path, trained_corpus)

    output = project_topic_classifier_items(
        classifier_corpus=trained_corpus,
        target_corpus=target,
        classifier_id="lab",
        extraction_snapshot=EXTRACTION_SNAPSHOT,
        item_ids=[" item-alpha "],
    )

    assert [item.item_id for item in output.items] == ["item-alpha"]
    assert output.recorded is False
    assert not (target.meta_dir / "topic-classifiers").exists()


def test_projection_reraises_non_eligibility_errors(
    tmp_path: Path, trained_corpus: _FakeCorpus
) -> None:
    """Propagate value errors that are not text eligibility problems."""
    target = _build_projection_pair(tmp_path, trained_corpus)

    with pytest.raises(ValueError, match="top_k must be at least 1"):
        project_topic_classifier_items(
            classifier_corpus=trained_corpus,
            target_corpus=target,
            classifier_id="lab",
            extraction_snapshot=EXTRACTION_SNAPSHOT,
            project_all=True,
            top_k=0,
        )


def test_projection_rejects_unknown_item_identifier(
    tmp_path: Path, trained_corpus: _FakeCorpus
) -> None:
    """Report unknown target item identifiers."""
    target = _build_projection_pair(tmp_path, trained_corpus)

    with pytest.raises(KeyError, match="Unknown item id: item-missing"):
        project_topic_classifier_items(
            classifier_corpus=trained_corpus,
            target_corpus=target,
            classifier_id="lab",
            extraction_snapshot=EXTRACTION_SNAPSHOT,
            item_ids=["item-missing"],
        )


def test_selected_projection_item_ids_sorts_catalog_when_order_is_empty() -> None:
    """Fall back to sorted catalog identifiers when no order is recorded."""
    selected = topic_classifier._selected_projection_item_ids(
        catalog_order=[],
        catalog_items={"b": object(), "a": object()},
        project_all=True,
        item_ids=[],
    )

    assert selected == ["a", "b"]


def test_selected_projection_item_ids_rejects_empty_catalog() -> None:
    """Reject projecting an empty target corpus."""
    with pytest.raises(ValueError, match="target corpus has no items"):
        topic_classifier._selected_projection_item_ids(
            catalog_order=[], catalog_items={}, project_all=True, item_ids=[]
        )


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Missing extracted text for item x in snapshot y", True),
        ("Extracted text for item x is empty", True),
        ("Extracted text for item x is shorter than min_text_characters 9", True),
        ("Extracted text for item x is odd", False),
        ("top_k must be at least 1", False),
    ],
)
def test_projection_text_eligibility_error_classification(message: str, expected: bool) -> None:
    """Classify which value errors mean an item should be skipped."""
    assert topic_classifier._is_projection_text_eligibility_error(ValueError(message)) is expected


def test_projection_summary_counts_unmapped_and_review_items() -> None:
    """Summarize mapped, unmapped and review-recommended projection rows."""
    common = {
        "classifier_id": "lab",
        "model_version": "v1",
        "classifier_corpus_uri": "file:///a",
        "target_corpus_uri": "file:///b",
        "extraction_snapshot": {},
    }
    items = [
        TopicClassifierProjectionItem(
            item_id="one",
            bertopic_topic_id=0,
            topic_uid="agents",
            review_recommended=False,
            **common,
        ),
        TopicClassifierProjectionItem(
            item_id="two", bertopic_topic_id=1, topic_uid=None, review_recommended=True, **common
        ),
    ]

    summary = topic_classifier._projection_summary(items, [])

    assert summary == {
        "projected_items": 2,
        "skipped_items": 0,
        "mapped_items": 1,
        "unmapped_items": 1,
        "review_recommended_items": 1,
    }


def test_prepare_text_document_rejects_text_shorter_than_minimum() -> None:
    """Reject text shorter than the configured minimum character count."""
    configuration = TopicModelingConfiguration.model_validate(
        {"text_source": {"min_text_characters": 50}}
    )

    with pytest.raises(ValueError, match="shorter than min_text_characters 50"):
        topic_classifier._prepare_text_document(
            item_id="short", text="tiny text", config=configuration
        )


def test_prepare_text_document_strips_and_preserves_identity() -> None:
    """Return a stripped document that keeps the item identity."""
    document = topic_classifier._prepare_text_document(
        item_id="doc", text="  hello world  ", config=TopicModelingConfiguration()
    )

    assert document.document_id == "doc"
    assert document.source_item_id == "doc"
    assert document.text == "hello world"


@pytest.mark.parametrize(
    ("patched_name", "expected_message"),
    [
        ("_apply_llm_extraction", "requires exactly one processed document"),
        ("_apply_entity_removal", "requires exactly one entity-processed document"),
        ("_apply_lexical_processing", "requires exactly one lexical document"),
    ],
)
def test_prepare_text_document_requires_one_document_per_stage(
    monkeypatch: pytest.MonkeyPatch, patched_name: str, expected_message: str
) -> None:
    """Reject preprocessing stages that do not return exactly one document."""
    document = TopicModelingDocument(document_id="d", source_item_id="d", text="text")
    monkeypatch.setattr(
        topic_classifier,
        patched_name,
        lambda **_: (_build_stage_report(2), [document, document]),
    )

    with pytest.raises(ValueError, match=expected_message):
        topic_classifier._prepare_text_document(
            item_id="d", text="text", config=TopicModelingConfiguration()
        )


def test_topic_candidate_probabilities_unwraps_tuple_output() -> None:
    """Return the first element of tuple outputs from approximate_distribution."""
    model = SimpleNamespace(approximate_distribution=lambda texts: ([{0: 0.5}], "extra"))

    assert topic_classifier._topic_candidate_probabilities(topic_model=model, text="t") == [
        {0: 0.5}
    ]


def test_topic_candidate_probabilities_returns_plain_output() -> None:
    """Return non-tuple outputs from approximate_distribution unchanged."""
    model = SimpleNamespace(approximate_distribution=lambda texts: [{0: 0.5}])

    assert topic_classifier._topic_candidate_probabilities(topic_model=model, text="t") == [
        {0: 0.5}
    ]


def test_candidates_from_probabilities_returns_empty_without_row() -> None:
    """Return no candidates when probabilities are unavailable."""
    assert (
        topic_classifier._topic_candidates_from_probabilities(
            probabilities=None, index=0, topic_map={}, top_k=3
        )
        == []
    )


def test_candidates_from_probabilities_orders_ties_by_topic_id_and_limits() -> None:
    """Order equal scores by topic identifier and honor top_k."""
    topic_map = {
        "mappings": [
            {"bertopic_topic_id": 1, "topic_uid": "b", "display_name": "B"},
            {"bertopic_topic_id": 2, "topic_uid": "c", "display_name": "C"},
            {"bertopic_topic_id": 3, "topic_uid": "d", "display_name": "D"},
        ]
    }

    candidates = topic_classifier._topic_candidates_from_probabilities(
        probabilities=[{3: 0.2, 2: 0.4, 1: 0.4, 9: 0.99}], index=0, topic_map=topic_map, top_k=2
    )

    assert [candidate.bertopic_topic_id for candidate in candidates] == [1, 2]
    assert [candidate.rank for candidate in candidates] == [1, 2]


def test_candidate_for_topic_skips_unmapped_when_mapped_only() -> None:
    """Return nothing for unmapped topics when only mapped candidates are wanted."""
    assert (
        topic_classifier._topic_candidate_for_topic(
            topic_id=4, score=0.5, topic_map={}, rank=1, mapped_only=True
        )
        is None
    )


def test_candidate_for_topic_uses_discovered_evidence() -> None:
    """Describe discovered topics with their keywords and document identifiers."""
    topic_map = {
        "discovered": [
            {"bertopic_topic_id": 4, "keywords": [{"keyword": "k"}], "document_ids": ["d"]}
        ]
    }

    candidate = topic_classifier._topic_candidate_for_topic(
        topic_id=4, score=0.5, topic_map=topic_map, rank=1, mapped_only=False
    )

    assert candidate.topic_uid is None
    assert candidate.representative_evidence["discovered"] is True
    assert candidate.representative_evidence["document_ids"] == ["d"]


def test_prediction_falls_back_to_assigned_topic_without_candidates() -> None:
    """Use the assigned topic and its score when no ranked candidates exist."""
    topic_map = {"discovered": [{"bertopic_topic_id": 7, "keywords": [], "document_ids": ["o"]}]}

    prediction = topic_classifier._prediction_from_topic(
        classifier_id="lab",
        item_id="x",
        model_version="v1",
        topic_id=7,
        score=0.8,
        probabilities=None,
        topic_map=topic_map,
        review_threshold=0.35,
        top_k=3,
        recorded=False,
    )

    assert prediction.bertopic_topic_id == 7
    assert prediction.topic_uid is None
    assert prediction.score == 0.8
    assert prediction.review_recommended is True
    assert len(prediction.topic_candidates) == 1


def test_prediction_accepts_unscored_mapped_candidate() -> None:
    """Treat a mapped candidate without a score as confident."""
    topic_map = {"mappings": [{"bertopic_topic_id": 2, "topic_uid": "u", "display_name": "U"}]}

    prediction = topic_classifier._prediction_from_topic(
        classifier_id="lab",
        item_id="x",
        model_version="v1",
        topic_id=2,
        score=None,
        probabilities=None,
        topic_map=topic_map,
        review_threshold=0.35,
        top_k=3,
        recorded=True,
    )

    assert prediction.topic_uid == "u"
    assert prediction.display_name == "U"
    assert prediction.score is None
    assert prediction.review_recommended is False
    assert prediction.recorded is True


class _ArrayLikeRows:
    def __init__(self, rows: List[Any]) -> None:
        self.rows = rows

    def tolist(self) -> List[Any]:
        return self.rows


@pytest.mark.parametrize(
    ("probabilities", "expected"),
    [
        (None, None),
        (5, None),
        ([], None),
        ({}, None),
        ([0.4], {0: 0.4}),
        ([{"2": 0.5, "3": "bad"}], {2: 0.5}),
        ([[0.1, "x", 0.3]], {0: 0.1, 2: 0.3}),
        (["text"], None),
        (_ArrayLikeRows([[0.25, 0.75]]), {0: 0.25, 1: 0.75}),
    ],
)
def test_probability_row_normalizes_supported_shapes(probabilities: Any, expected: Any) -> None:
    """Normalize probability containers into topic score mappings."""
    assert topic_classifier._probability_row(probabilities, index=0) == expected


def test_probability_score_prefers_assigned_topic() -> None:
    """Return the score recorded for the assigned topic."""
    assert topic_classifier._probability_score([{1: 0.3, 2: 0.6}], index=0, topic_id=1) == 0.3


def test_probability_score_falls_back_to_maximum_score() -> None:
    """Return the highest score when the assigned topic has none."""
    assert topic_classifier._probability_score([{1: 0.3, 2: 0.6}], index=0, topic_id=9) == 0.6


def test_probability_score_is_none_for_empty_row() -> None:
    """Return no score when the row has no numeric entries."""
    assert topic_classifier._probability_score([{}], index=0, topic_id=1) is None
    assert topic_classifier._probability_score(None, index=0, topic_id=1) is None


def test_proposed_topic_uid_reads_curation_metadata() -> None:
    """Read and strip the proposed topic from curation metadata."""
    proposed = topic_classifier._proposed_topic_uid({"curation": {"proposed_topic_uid": " x "}})

    assert proposed == "x"


@pytest.mark.parametrize(
    "metadata",
    [{}, {"curation": "text"}, {"curation": {}}, {"curation": {"proposed_topic_uid": "  "}}],
)
def test_proposed_topic_uid_is_none_without_usable_value(metadata: Dict[str, Any]) -> None:
    """Return no proposed topic when curation metadata lacks a usable value."""
    assert topic_classifier._proposed_topic_uid(metadata) is None


def test_candidate_filters_require_matching_tag_and_proposal() -> None:
    """Select items only when both provided filters match."""
    item = _build_catalog_item(
        "i", tags=["new"], metadata={"curation": {"proposed_topic_uid": "agents"}}
    )

    def matches(tag: Optional[str], proposal: Optional[str]) -> bool:
        return topic_classifier._catalog_item_matches_candidate_filters(
            item=item, candidate_tag=tag, proposed_topic_uid=proposal
        )

    assert matches("new", "agents") is True
    assert matches("old", None) is False
    assert matches(None, "speech") is False
    assert matches(None, None) is True


def test_unsupervised_topics_require_output_file(tmp_path: Path) -> None:
    """Report a missing exploratory topic modeling output."""
    corpus = _FakeCorpus(tmp_path)

    with pytest.raises(FileNotFoundError, match="Missing topic modeling output"):
        topic_classifier._load_unsupervised_topics_by_item(
            corpus=corpus, topic_modeling_snapshot_id="explore"
        )


def _write_unsupervised_output(corpus: _FakeCorpus, payload: Dict[str, Any]) -> None:
    output_path = corpus.analysis_dir / "topic-modeling" / "explore" / "output.json"
    output_path.parent.mkdir(parents=True)
    output_path.write_text(json.dumps(payload), encoding="utf-8")


def test_unsupervised_topics_index_documents_by_item(tmp_path: Path) -> None:
    """Index exploratory topic identifiers and keywords by document identifier."""
    corpus = _FakeCorpus(tmp_path)
    _write_unsupervised_output(
        corpus,
        {
            "report": {
                "topics": [
                    {"topic_id": 3, "keywords": [{"keyword": "k"}], "document_ids": ["a", "b"]},
                    {"topic_id": 4},
                ]
            }
        },
    )

    by_item = topic_classifier._load_unsupervised_topics_by_item(
        corpus=corpus, topic_modeling_snapshot_id="explore"
    )

    assert by_item == {
        "a": {"topic_id": 3, "keywords": [{"keyword": "k"}]},
        "b": {"topic_id": 3, "keywords": [{"keyword": "k"}]},
    }


def _build_review_row(
    *,
    review_recommended: bool,
    topic_uid: Optional[str],
    proposed: Optional[str],
    unsupervised_topic_id: Optional[int],
) -> topic_classifier.TopicClassifierBatchReviewItem:
    return topic_classifier.TopicClassifierBatchReviewItem(
        item_id="i",
        proposed_topic_uid=proposed,
        classifier_topic_uid=topic_uid,
        classifier_bertopic_topic_id=0,
        review_recommended=review_recommended,
        unsupervised_topic_id=unsupervised_topic_id,
    )


def test_batch_review_summary_of_no_rows_is_all_zero() -> None:
    """Summarize an empty batch without dividing by zero."""
    summary = topic_classifier._batch_review_summary([])

    assert summary["candidate_items"] == 0
    assert summary["review_recommended_rate"] == 0.0
    assert summary["classifier_unmapped_rate"] == 0.0
    assert summary["dominant_unsupervised_topic_id"] is None
    assert summary["topic_management_flags"]["batch_review_required"] is False


def test_batch_review_summary_flags_rates_and_dominant_topic() -> None:
    """Flag high rates, review-sized proposals and the dominant exploratory topic."""
    rows = [
        _build_review_row(
            review_recommended=True, topic_uid=None, proposed="vision", unsupervised_topic_id=2
        )
        for _ in range(5)
    ] + [
        _build_review_row(
            review_recommended=False, topic_uid="agents", proposed=None, unsupervised_topic_id=1
        )
    ]

    summary = topic_classifier._batch_review_summary(rows)

    assert summary["candidate_items"] == 6
    assert summary["review_recommended_items"] == 5
    assert summary["classifier_unmapped_items"] == 5
    assert summary["proposed_topic_counts"] == {"vision": 5}
    assert summary["unsupervised_topic_counts"] == {"1": 1, "2": 5}
    assert summary["dominant_unsupervised_topic_id"] == 2
    assert summary["topic_management_flags"] == {
        "batch_review_required": True,
        "classifier_unmapped_rate_exceeds_threshold": True,
        "review_recommended_rate_exceeds_threshold": True,
        "candidate_topic_reached_review_size": True,
    }


def test_batch_review_requires_candidate_selector(trained_corpus: _FakeCorpus) -> None:
    """Reject batch review without a tag or proposed topic selector."""
    with pytest.raises(ValueError, match="requires --candidate-tag or --proposed-topic-uid"):
        build_topic_classifier_batch_review(
            corpus=trained_corpus,
            classifier_id="lab",
            extraction_snapshot=EXTRACTION_SNAPSHOT,
            topic_modeling_snapshot_id="explore",
        )


def test_batch_review_classifies_selected_candidates_and_records(
    tmp_path: Path, trained_corpus: _FakeCorpus
) -> None:
    """Review tagged candidates in creation order with exploratory topics and audit records."""
    trained_corpus.catalog.items = {
        "item-delta": _build_catalog_item(
            "item-delta",
            tags=["candidate"],
            metadata={"curation": {"proposed_topic_uid": "speech"}},
            created_at="2026-02-01T00:00:00Z",
        ),
        "item-alpha": _build_catalog_item(
            "item-alpha", tags=["candidate"], created_at="2026-01-01T00:00:00Z"
        ),
        "item-beta": _build_catalog_item("item-beta", tags=["other"]),
    }
    _write_unsupervised_output(
        trained_corpus,
        {"report": {"topics": [{"topic_id": 3, "keywords": [], "document_ids": ["item-delta"]}]}},
    )

    review = build_topic_classifier_batch_review(
        corpus=trained_corpus,
        classifier_id="lab",
        extraction_snapshot=EXTRACTION_SNAPSHOT,
        topic_modeling_snapshot_id="explore",
        candidate_tag="candidate",
        record=True,
    )

    records_path = trained_corpus.meta_dir / "topic-classifiers" / "lab" / "predictions.jsonl"
    assert [row.item_id for row in review.items] == ["item-alpha", "item-delta"]
    assert review.items[1].proposed_topic_uid == "speech"
    assert review.items[1].unsupervised_topic_id == 3
    assert review.items[0].unsupervised_topic_id is None
    assert review.items[1].classifier_topic_uid == "speech"
    assert review.filters["record"] is True
    assert review.summary["candidate_items"] == 2
    assert len(records_path.read_text().splitlines()) == 2


def test_batch_review_filters_by_proposed_topic_without_recording(
    tmp_path: Path, trained_corpus: _FakeCorpus
) -> None:
    """Select candidates by proposed topic and skip audit records by default."""
    trained_corpus.catalog.items = {
        "item-delta": _build_catalog_item(
            "item-delta", metadata={"curation": {"proposed_topic_uid": "speech"}}
        ),
        "item-alpha": _build_catalog_item("item-alpha"),
    }
    _write_unsupervised_output(trained_corpus, {})

    review = build_topic_classifier_batch_review(
        corpus=trained_corpus,
        classifier_id="lab",
        extraction_snapshot=EXTRACTION_SNAPSHOT,
        topic_modeling_snapshot_id="explore",
        proposed_topic_uid="speech",
    )

    assert [row.item_id for row in review.items] == ["item-delta"]
    assert review.filters["proposed_topic_uid"] == "speech"
    assert not (trained_corpus.meta_dir / "topic-classifiers").exists()
