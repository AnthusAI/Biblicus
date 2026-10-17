from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest
import yaml
from pydantic import ValidationError

import biblicus.ontology as ontology
import biblicus.research_intake as research_intake
import biblicus.steering_feedback as steering_feedback
import biblicus.taxonomy as taxonomy
from biblicus.research_intake import ResearchIntakeConfiguration


def _suppression(
    *,
    suppression_id: str,
    proposal_kind: str,
    scope: Optional[Dict[str, Any]] = None,
    match: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "suppression_id": suppression_id,
        "proposal_id": f"{proposal_kind}:x",
        "proposal_kind": proposal_kind,
        "steering_domain": "topic",
        "reason": "Reviewed.",
        "decided_at": "2026-05-16T00:00:00+00:00",
        "decided_by": "editor@example.com",
        "scope": {
            "topic_set_id": "topic-set-one",
            "corpus_id": "corpus-one",
            "classifier_id": None,
            "root_topic_uid": None,
            **(scope or {}),
        },
        "match": {
            "topic_uid": None,
            "display_name": None,
            "normalized_display_name": None,
            "relationship_type": None,
            "graph_entity_id": None,
            **(match or {}),
        },
        "evidence_item_ids": [],
    }


def _feedback_payload(suppressions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "export_kind": "papyrus-steering-feedback",
        "generated_at": "2026-05-16T00:00:00+00:00",
        "source": {
            "system": "papyrus",
            "topic_set_id": "topic-set-one",
            "corpus_id": "corpus-one",
            "classifier_id": "steering-classifier",
        },
        "topic_set": {
            "topic_set_id": "topic-set-one",
            "corpus_id": "corpus-one",
            "classifier_id": "steering-classifier",
            "display_name": "Topic Set",
            "description": "Reviewed topics.",
        },
        "decisions": [],
        "accepted_proposals": [],
        "rejected_proposals": [],
        "suppressions": suppressions,
    }


def _feedback(suppressions: List[Dict[str, Any]]) -> steering_feedback.SteeringFeedback:
    return steering_feedback.SteeringFeedback.model_validate(_feedback_payload(suppressions))


def _signal(kind: str, payload: Any) -> SimpleNamespace:
    return SimpleNamespace(signal_kind=kind, payload=payload)


def test_feedback_rejects_unsupported_schema_version() -> None:
    """A steering feedback export with a foreign schema version is rejected."""
    payload = _feedback_payload([])
    payload["schema_version"] = 99
    with pytest.raises(ValidationError, match="Unsupported steering feedback schema_version"):
        steering_feedback.SteeringFeedback.model_validate(payload)


def test_feedback_export_kind_validator_rejects_other_kinds() -> None:
    """The export kind validator raises for kinds other than the Papyrus export."""
    with pytest.raises(ValueError, match="Unsupported steering feedback export_kind: other"):
        steering_feedback.SteeringFeedback._validate_export_kind("other")
    assert (
        steering_feedback.SteeringFeedback._validate_export_kind("papyrus-steering-feedback")
        == "papyrus-steering-feedback"
    )


def test_load_steering_feedback_reports_missing_and_invalid_json(tmp_path: Path) -> None:
    """Missing files and invalid JSON produce descriptive errors."""
    with pytest.raises(FileNotFoundError, match="Steering feedback file not found"):
        steering_feedback.load_steering_feedback(tmp_path / "absent.json")
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid steering feedback JSON"):
        steering_feedback.load_steering_feedback(broken)


def test_suppression_lookups_return_none_without_feedback() -> None:
    """Both suppression lookups return nothing when there is no feedback export."""
    assert (
        steering_feedback.taxonomy_candidate_suppression(
            feedback=None,
            classifier_id="c",
            root_topic_uid="r",
            topic_uid="t",
            display_name="T",
        )
        is None
    )
    assert (
        steering_feedback.graph_signal_suppression(
            feedback=None, classifier_id="c", signal=_signal("possible-duplicate-entity", {})
        )
        is None
    )


def test_taxonomy_suppression_skips_other_kinds_and_scopes() -> None:
    """Non-taxonomy kinds, other root topics, and unmatched candidates are skipped."""
    feedback = _feedback(
        [
            _suppression(
                suppression_id="wrong-kind",
                proposal_kind="create-topic-entity",
                match={"topic_uid": "child"},
            ),
            _suppression(
                suppression_id="wrong-root",
                proposal_kind="create-taxonomy-node",
                scope={"root_topic_uid": "other-root"},
                match={"topic_uid": "child"},
            ),
            _suppression(
                suppression_id="no-match",
                proposal_kind="create-taxonomy-node",
                match={"topic_uid": "different"},
            ),
        ]
    )
    result = steering_feedback.taxonomy_candidate_suppression(
        feedback=feedback,
        classifier_id="c",
        root_topic_uid="root",
        topic_uid="child",
        display_name="Child",
    )
    assert result is None


def test_graph_suppression_ignores_unknown_signal_kinds_and_non_mapping_payloads() -> None:
    """Unknown signal kinds never match and non-mapping payloads are treated as empty."""
    feedback = _feedback(
        [
            _suppression(
                suppression_id="dup",
                proposal_kind="merge-entities",
                match={"topic_uid": "x"},
            )
        ]
    )
    assert (
        steering_feedback.graph_signal_suppression(
            feedback=feedback, classifier_id="c", signal=_signal("unknown-kind", {})
        )
        is None
    )
    assert (
        steering_feedback.graph_signal_suppression(
            feedback=feedback,
            classifier_id="c",
            signal=_signal("possible-duplicate-entity", "not-a-dict"),
        )
        is None
    )


def test_graph_suppression_filters_by_proposal_kind_and_scope() -> None:
    """Suppressions of another kind or scoped to another classifier or root are skipped."""
    feedback = _feedback(
        [
            _suppression(
                suppression_id="other-kind",
                proposal_kind="create-topic-entity",
                match={"topic_uid": "left"},
            ),
            _suppression(
                suppression_id="other-classifier",
                proposal_kind="merge-entities",
                scope={"classifier_id": "someone-else"},
                match={"topic_uid": "left"},
            ),
            _suppression(
                suppression_id="other-root",
                proposal_kind="merge-entities",
                scope={"root_topic_uid": "elsewhere"},
                match={"topic_uid": "left"},
            ),
        ]
    )
    result = steering_feedback.graph_signal_suppression(
        feedback=feedback,
        classifier_id="c",
        signal=_signal("possible-duplicate-entity", {"left_topic_uid": "left"}),
    )
    assert result is None


@pytest.mark.parametrize(
    ("match", "payload"),
    [
        ({"relationship_type": "part-of"}, {"edge_type": "part-of"}),
        ({"graph_entity_id": "node-7"}, {"entity_id": "node-7"}),
        ({"display_name": "Some  Label"}, {"labels": ["some label", 3]}),
        ({"normalized_display_name": "canonical name"}, {"canonical": "Canonical Name"}),
    ],
)
def test_graph_suppression_matches_each_match_field(
    match: Dict[str, Any], payload: Dict[str, Any]
) -> None:
    """Each match field type can independently trigger a graph suppression."""
    feedback = _feedback(
        [_suppression(suppression_id="hit", proposal_kind="merge-entities", match=match)]
    )
    result = steering_feedback.graph_signal_suppression(
        feedback=feedback,
        classifier_id="c",
        signal=_signal("possible-duplicate-entity", payload),
    )
    assert result is not None
    assert result.suppression_id == "hit"


def test_graph_suppression_requires_a_matching_field_when_scope_matches() -> None:
    """A scope-matching suppression without a matching field does not suppress the signal."""
    feedback = _feedback(
        [
            _suppression(
                suppression_id="miss",
                proposal_kind="merge-entities",
                match={
                    "relationship_type": "part-of",
                    "graph_entity_id": "node-1",
                    "display_name": "Nothing Similar",
                },
            )
        ]
    )
    result = steering_feedback.graph_signal_suppression(
        feedback=feedback,
        classifier_id="c",
        signal=_signal(
            "possible-duplicate-entity",
            {"edge_type": "other", "entity_id": "node-2", "label": "Unrelated"},
        ),
    )
    assert result is None


def test_normalize_feedback_text_handles_blank_values() -> None:
    """Blank and missing text normalize to nothing."""
    assert steering_feedback.normalize_feedback_text(None) is None
    assert steering_feedback.normalize_feedback_text("   ") is None


def test_intake_configuration_rejects_blank_and_duplicate_field_paths() -> None:
    """Field path lists reject blank entries and duplicates."""
    with pytest.raises(ValidationError, match="field paths must contain non-empty values"):
        ResearchIntakeConfiguration(required_fields=["title", " "])
    with pytest.raises(ValidationError, match="field paths contain duplicate values: title"):
        ResearchIntakeConfiguration(required_fields=["title", "title"])


def test_decide_research_intake_item_rejects_delete_on_accept() -> None:
    """Deleting is only allowed together with a reject decision."""
    corpus = SimpleNamespace(get_item=lambda item_id: SimpleNamespace(id=item_id))
    with pytest.raises(ValueError, match="--delete is only supported when rejecting"):
        research_intake.decide_research_intake_item(
            corpus=corpus, item_id="item", decision="accept", topic_uid=None, delete=True
        )


def test_decide_research_intake_item_deletes_rejected_item(tmp_path: Path) -> None:
    """Rejecting with delete removes the item and reindexes the corpus."""
    calls: List[str] = []
    corpus = SimpleNamespace(
        root=tmp_path,
        get_item=lambda item_id: SimpleNamespace(id=item_id),
        delete_item=lambda item_id: calls.append(f"delete:{item_id}"),
        reindex=lambda: calls.append("reindex"),
    )
    output = research_intake.decide_research_intake_item(
        corpus=corpus, item_id="item-1", decision="reject", topic_uid=None, delete=True
    )
    assert calls == ["delete:item-1", "reindex"]
    assert output.decision == "rejected"
    assert output.reason == "Human decision: rejected (deleted)."


def test_status_from_human_decision_validates_input() -> None:
    """Only accept and reject are valid human decisions."""
    assert research_intake._status_from_human_decision(" Accept ") == "accepted"
    with pytest.raises(ValueError, match="decision must be accept or reject"):
        research_intake._status_from_human_decision("maybe")


def test_nearest_corpus_evidence_handles_empty_candidates_and_skips_unreviewed() -> None:
    """Empty candidates return nothing and pending or rejected items are not evidence."""
    items = {
        "good": SimpleNamespace(
            id="good", title="Agent memory", metadata={"abstract": "memory for agents"}
        ),
        "pending": SimpleNamespace(
            id="pending",
            title="Agent memory",
            metadata={"curation": {"intake_status": "pending_review"}},
        ),
        "rejected": SimpleNamespace(
            id="rejected",
            title="Agent memory",
            metadata={"curation": {"intake_status": "rejected"}},
        ),
    }
    corpus = SimpleNamespace(load_catalog=lambda: SimpleNamespace(items=items))
    assert research_intake.nearest_corpus_evidence(corpus=corpus, candidate_text="", limit=2) == []
    ranked = research_intake.nearest_corpus_evidence(
        corpus=corpus, candidate_text="agent memory", limit=2
    )
    assert [item_id for item_id, _ in ranked] == ["good"]


def test_resolved_media_type_prefers_argument_then_metadata_then_guess() -> None:
    """Media type resolution follows argument, metadata, filename guess, then binary default."""
    path = Path("paper.pdf")
    assert (
        research_intake._resolved_media_type(
            source_path=path, metadata={"media_type": "text/plain"}, media_type=" text/html "
        )
        == "text/html"
    )
    assert (
        research_intake._resolved_media_type(
            source_path=path, metadata={"media_type": "text/plain"}, media_type=None
        )
        == "text/plain"
    )
    assert (
        research_intake._resolved_media_type(source_path=path, metadata={}, media_type=None)
        == "application/pdf"
    )
    assert (
        research_intake._resolved_media_type(
            source_path=Path("data.unknownext"), metadata={}, media_type=" "
        )
        == "application/octet-stream"
    )


def test_metadata_tags_accepts_strings_lists_and_rejects_other_types() -> None:
    """Tags may be absent, a string, or a list of strings, and nothing else."""
    assert research_intake._metadata_tags({}) == []
    assert research_intake._metadata_tags({"tags": " solo "}) == ["solo"]
    assert research_intake._metadata_tags({"tags": ["a", " b ", "", 3]}) == ["a", "b"]
    with pytest.raises(ValueError, match="tags must be a string or list of strings"):
        research_intake._metadata_tags({"tags": 7})
    with pytest.raises(ValueError, match="tags must be a string or list of strings"):
        research_intake._metadata_tags({"tags": "  "})


def test_metadata_string_ignores_blank_and_non_string_values() -> None:
    """Only non-blank strings are returned from metadata string lookup."""
    assert research_intake._metadata_string({"k": " v "}, "k") == "v"
    assert research_intake._metadata_string({"k": "  "}, "k") is None
    assert research_intake._metadata_string({"k": 3}, "k") is None


def test_update_tags_adds_removes_and_deduplicates() -> None:
    """Tag updates remove requested tags, add new ones, and keep order without duplicates."""
    updated = research_intake._update_tags(
        existing=["keep", "drop", ""],
        tags_add=["new", " keep ", "new", "", "extra"],
        tags_remove=["drop", " "],
    )
    assert updated == ["keep", "new", "extra"]


def _sidecar_item(relpath: str, metadata: Dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(relpath=relpath, media_type="application/pdf", metadata=metadata)


def test_update_item_curation_rewrites_sidecar_and_clears_tags(tmp_path: Path) -> None:
    """Human decisions are written to the sidecar and removing all tags drops the tag field."""
    content = tmp_path / "paper.pdf"
    content.write_bytes(b"%PDF")
    sidecar = tmp_path / "paper.pdf.biblicus.yml"
    sidecar.write_text(yaml.safe_dump({"tags": ["only"], "title": "Paper"}), encoding="utf-8")
    corpus = SimpleNamespace(root=tmp_path)
    item = _sidecar_item("paper.pdf", {})
    metadata = research_intake._update_item_curation(
        corpus=corpus,
        item=item,
        status="accepted",
        topic_uid="agents",
        tags_add=[],
        tags_remove=["only"],
    )
    stored = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
    assert "tags" not in metadata
    assert "tags" not in stored
    assert stored["curation"]["intake_status"] == "accepted"
    assert stored["curation"]["reviewed_topic_uid"] == "agents"
    assert stored["curation"]["intake_assessment"]["human_decision"] == "accepted"


def test_update_item_curation_sets_tags_without_sidecar(tmp_path: Path) -> None:
    """Without a sidecar the catalog metadata seeds the new sidecar and tags are applied."""
    (tmp_path / "paper.pdf").write_bytes(b"%PDF")
    corpus = SimpleNamespace(root=tmp_path)
    item = _sidecar_item("paper.pdf", {"tags": ["old"], "curation": {"intake_assessment": {}}})
    metadata = research_intake._update_item_curation(
        corpus=corpus,
        item=item,
        status="rejected",
        topic_uid=None,
        tags_add=["fresh"],
        tags_remove=[],
    )
    assert metadata["tags"] == ["old", "fresh"]
    assert (tmp_path / "paper.pdf.biblicus.yml").is_file()


def test_load_mutable_item_metadata_rejects_non_mapping_sidecar(tmp_path: Path) -> None:
    """A sidecar that is not a mapping is reported as an error."""
    (tmp_path / "paper.pdf").write_bytes(b"%PDF")
    (tmp_path / "paper.pdf.biblicus.yml").write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Sidecar metadata must be a mapping/object"):
        research_intake._load_mutable_item_metadata(
            corpus=SimpleNamespace(root=tmp_path), item=_sidecar_item("paper.pdf", {})
        )


def test_load_mutable_item_metadata_rewrites_markdown_front_matter(tmp_path: Path) -> None:
    """Markdown items are updated through their front matter."""
    path = tmp_path / "note.md"
    path.write_text("---\ntitle: Note\n---\nBody text\n", encoding="utf-8")
    item = SimpleNamespace(relpath="note.md", media_type="text/markdown", metadata={})
    metadata, writer = research_intake._load_mutable_item_metadata(
        corpus=SimpleNamespace(root=tmp_path), item=item
    )
    metadata["title"] = "Changed"
    writer(metadata)
    assert "title: Changed" in path.read_text(encoding="utf-8")
    assert "Body text" in path.read_text(encoding="utf-8")


def test_intake_cosine_similarity_handles_empty_and_zero_vectors() -> None:
    """Empty and zero-norm vectors have zero similarity."""
    counter = research_intake.Counter
    assert research_intake._cosine_similarity(counter(), counter({"a": 1})) == 0.0
    assert research_intake._cosine_similarity(counter({"a": 0}), counter({"a": 0})) == 0.0
    assert research_intake._cosine_similarity(counter({"a": 1}), counter({"a": 1})) == (
        pytest.approx(1.0)
    )


def test_intake_status_and_assessment_ignore_malformed_curation() -> None:
    """Malformed curation blocks yield no status and an empty assessment."""
    assert research_intake._intake_status({"curation": "text"}) is None
    assert research_intake._intake_status({"curation": {"intake_status": " "}}) is None
    assert research_intake._intake_status({"curation": {"intake_status": " ok "}}) == "ok"
    assert research_intake._intake_assessment({"curation": "text"}) == {}
    assert research_intake._intake_assessment({"curation": {"intake_assessment": 3}}) == {}
    assert research_intake._intake_assessment({"curation": {"intake_assessment": {"a": 1}}}) == {
        "a": 1
    }


def _write_manifest(directory: Path, payload: Dict[str, Any]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "latest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ontology_required_snapshot_ids_reject_missing_values() -> None:
    """Ontology and taxonomy manifests without snapshot identifiers are rejected."""
    with pytest.raises(ValueError, match="Ontology manifest snapshot_id is missing"):
        ontology._required_snapshot_id(SimpleNamespace(snapshot_id=None))
    with pytest.raises(ValueError, match="Taxonomy manifest snapshot_id is missing"):
        ontology._required_taxonomy_snapshot_id(SimpleNamespace(snapshot_id=None))
    assert ontology._required_taxonomy_snapshot_id(SimpleNamespace(snapshot_id="t")) == "t"


def test_taxonomy_required_snapshot_id_rejects_missing_value() -> None:
    """Taxonomy manifests without a snapshot identifier are rejected."""
    with pytest.raises(ValueError, match="Taxonomy manifest snapshot_id is missing"):
        taxonomy._required_snapshot_id(SimpleNamespace(snapshot_id=None))
    assert taxonomy._required_snapshot_id(SimpleNamespace(snapshot_id="t")) == "t"


def test_resolve_latest_pointers_validate_contents(tmp_path: Path) -> None:
    """Latest pointers must exist and contain a non-blank snapshot identifier."""
    corpus = SimpleNamespace(analysis_dir=tmp_path)
    assert ontology._resolve_ontology_snapshot_id(corpus=corpus, snapshot_id="fixed") == "fixed"
    assert taxonomy._resolve_taxonomy_snapshot_id(corpus=corpus, snapshot_id="fixed") == "fixed"
    with pytest.raises(FileNotFoundError, match="Missing ontology latest pointer"):
        ontology._resolve_ontology_snapshot_id(corpus=corpus, snapshot_id="latest")
    with pytest.raises(FileNotFoundError, match="Missing taxonomy latest pointer"):
        taxonomy._resolve_taxonomy_snapshot_id(corpus=corpus, snapshot_id="latest")
    _write_manifest(tmp_path / "ontology", {"snapshot_id": " "})
    _write_manifest(tmp_path / "taxonomy", {"snapshot_id": 4})
    with pytest.raises(ValueError, match="Ontology latest pointer must contain snapshot_id"):
        ontology._resolve_ontology_snapshot_id(corpus=corpus, snapshot_id="latest")
    with pytest.raises(ValueError, match="Taxonomy latest pointer must contain snapshot_id"):
        taxonomy._resolve_taxonomy_snapshot_id(corpus=corpus, snapshot_id="latest")
    _write_manifest(tmp_path / "ontology", {"snapshot_id": "resolved-o"})
    _write_manifest(tmp_path / "taxonomy", {"snapshot_id": "resolved-t"})
    assert ontology._resolve_ontology_snapshot_id(corpus=corpus, snapshot_id="latest") == (
        "resolved-o"
    )
    assert taxonomy._resolve_taxonomy_snapshot_id(corpus=corpus, snapshot_id="latest") == (
        "resolved-t"
    )


def test_apply_ontology_to_graph_writes_overlay_and_closes_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Applying an ontology writes the overlay records and always closes the driver."""
    events: Dict[str, Any] = {}

    class _Driver:
        def close(self) -> None:
            events["closed"] = True

    reference = SimpleNamespace(
        extractor_id="graph-extractor",
        snapshot_id="graph-snap",
        as_string=lambda: "graph-extractor:graph-snap",
    )
    nodes = [SimpleNamespace(), SimpleNamespace()]
    edges = [SimpleNamespace(edge_type="part-of"), SimpleNamespace(edge_type="related-to")]
    monkeypatch.setattr(
        ontology,
        "load_recorded_taxonomy_manifest",
        lambda **_: SimpleNamespace(snapshot_id="tax-1"),
    )
    monkeypatch.setattr(
        ontology,
        "load_recorded_ontology_manifest",
        lambda **_: SimpleNamespace(snapshot_id="onto-1"),
    )
    monkeypatch.setattr(ontology, "parse_graph_snapshot_reference", lambda _: reference)
    monkeypatch.setattr(
        ontology,
        "load_graph_snapshot_manifest",
        lambda *_, **__: SimpleNamespace(graph_id="graph-1"),
    )
    monkeypatch.setattr(ontology, "build_ontology_graph_overlay", lambda **_: (nodes, edges))
    monkeypatch.setattr(ontology, "resolve_neo4j_settings", lambda: "settings")
    monkeypatch.setattr(ontology, "create_neo4j_driver", lambda _: _Driver())
    monkeypatch.setattr(
        ontology, "write_graph_records", lambda **kwargs: events.update(written=kwargs)
    )
    output = ontology.apply_ontology_to_graph(
        corpus=SimpleNamespace(uri="file:///corpus"),
        taxonomy_snapshot_id="latest",
        ontology_snapshot_id="latest",
        graph_snapshot="graph-extractor:graph-snap",
    )
    assert events["closed"] is True
    assert events["written"]["graph_id"] == "graph-1"
    assert output.nodes_written == 2
    assert output.edges_written == 2
    assert output.edge_types == ["part-of", "related-to"]
    assert output.taxonomy_snapshot_id == "tax-1"
    assert output.ontology_snapshot_id == "onto-1"


def test_topic_map_member_ids_skip_malformed_entries() -> None:
    """Malformed topics and mappings are ignored while valid members are merged."""
    member_ids = taxonomy._topic_map_member_ids(
        {
            "topics": [
                "text",
                {"topic_uid": " "},
                {"topic_uid": "a", "seed_item_ids": ["2", "1"], "holdout_item_ids": ["3"]},
            ],
            "mappings": [
                "text",
                {"topic_uid": 5},
                {"topic_uid": "a", "document_ids": ["1", "4"]},
                {"topic_uid": "b", "document_ids": ["9"]},
            ],
        }
    )
    assert member_ids == {"a": ["1", "2", "3", "4"], "b": ["9"]}


def _topic_modeling_config(
    *,
    umap_parameters: Optional[Dict[str, Any]] = None,
    hdbscan_parameters: Optional[Dict[str, Any]] = None,
    bertopic_parameters: Optional[Dict[str, Any]] = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        bertopic_analysis=SimpleNamespace(
            parameters=bertopic_parameters or {},
            umap_model=(
                SimpleNamespace(parameters=umap_parameters) if umap_parameters is not None else None
            ),
            hdbscan_model=(
                SimpleNamespace(parameters=hdbscan_parameters)
                if hdbscan_parameters is not None
                else None
            ),
        )
    )


def test_positive_int_parameter_accepts_only_positive_integers() -> None:
    """Only positive non-boolean integers count as valid parameters."""
    assert taxonomy._positive_int_parameter(3) == 3
    assert taxonomy._positive_int_parameter(0) is None
    assert taxonomy._positive_int_parameter(True) is None
    assert taxonomy._positive_int_parameter("3") is None


def test_effective_umap_components_cover_configured_and_default_sources() -> None:
    """UMAP component sources distinguish configured, declared, and default settings."""
    assert taxonomy._effective_umap_n_components(
        _topic_modeling_config(umap_parameters={"n_components": 4})
    ) == (4, "Configured")
    assert taxonomy._effective_umap_n_components(
        _topic_modeling_config(bertopic_parameters={"umap_model": object()})
    ) == (None, "Configured")
    components, source = taxonomy._effective_umap_n_components(_topic_modeling_config())
    assert components == taxonomy.BERTOPIC_DEFAULT_UMAP_N_COMPONENTS
    assert source == "BERTopic default"


def test_document_requirement_uses_largest_requirement() -> None:
    """The scoped document requirement is the largest of the configured minimums."""
    minimum, reason = taxonomy._scoped_topic_modeling_document_requirement(
        _topic_modeling_config(
            umap_parameters={"n_components": 3}, hdbscan_parameters={"min_cluster_size": 20}
        )
    )
    assert minimum == 20
    assert "HDBSCAN min_cluster_size=20" in reason
    minimum, reason = taxonomy._scoped_topic_modeling_document_requirement(
        _topic_modeling_config(
            umap_parameters={"n_components": 3}, hdbscan_parameters={"min_cluster_size": "x"}
        )
    )
    assert minimum == 5
    assert "Configured UMAP n_components=3" in reason


def test_scoped_skip_warning_describes_each_threshold() -> None:
    """Skip warnings are absent when enough documents exist and descriptive otherwise."""
    config = _topic_modeling_config(
        umap_parameters={"n_components": 3}, hdbscan_parameters={"min_cluster_size": 20}
    )
    assert (
        taxonomy._scoped_topic_modeling_skip_warning(root_uid="r", document_count=25, config=config)
        is None
    )
    detailed = taxonomy._scoped_topic_modeling_skip_warning(
        root_uid="r", document_count=4, config=config
    )
    assert detailed is not None
    assert "requires at least 20 documents" in detailed
    assert "found 4" in detailed
    simple_config = _topic_modeling_config(bertopic_parameters={"umap_model": object()})
    simple = taxonomy._scoped_topic_modeling_skip_warning(
        root_uid="r", document_count=1, config=simple_config
    )
    assert simple == "Skipping root topic r: taxonomy discovery requires at least two documents"


def test_list_pending_items_skips_items_that_are_not_pending(tmp_path: Path) -> None:
    """Only items awaiting review appear in the pending list."""
    pending = SimpleNamespace(
        id="p",
        title="Pending",
        source_uri=None,
        created_at="2026-01-01T00:00:00+00:00",
        metadata={
            "curation": {
                "intake_status": "pending_review",
                "intake_assessment": {"topic_uid": "agents", "classifier_score": 0.5},
            }
        },
    )
    accepted = SimpleNamespace(
        id="a",
        title="Accepted",
        source_uri=None,
        created_at="2026-01-02T00:00:00+00:00",
        metadata={"curation": {"intake_status": "accepted"}},
    )
    corpus = SimpleNamespace(
        root=tmp_path,
        load_catalog=lambda: SimpleNamespace(items={"p": pending, "a": accepted}),
    )
    output = research_intake.list_pending_research_intake_items(corpus=corpus)
    assert [item.item_id for item in output.items] == ["p"]
    assert output.items[0].topic_uid == "agents"
