"""Integration tests for HTML metadata through pipeline, snapshots, and graph NER."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from biblicus import extraction
from biblicus.corpus import Corpus
from biblicus.extractors import get_extractor
from biblicus.extractors.markitdown_text import MarkItDownExtractor
from biblicus.extractors.select_override import SelectOverrideExtractor
from biblicus.graph.extractors import ner_entities
from biblicus.graph.grobid_dedup import grobid_blocked_surface_forms, is_grobid_extraction_metadata
from biblicus.models import CatalogItem, ExtractedText, ExtractionStageOutput
from biblicus.extractors.html_web_metadata import HtmlWebMetadataExtractor

_FIXTURES = Path(__file__).parent / "fixtures" / "html_heuristics"
_RECIPE = Path(__file__).parent.parent / "configurations" / "extraction" / "ai-ml-research-topic-text.yml"


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _run_pipeline_stages(
    *,
    corpus: Corpus,
    item: CatalogItem,
    markitdown_text: str,
) -> tuple[ExtractedText | None, list[ExtractionStageOutput]]:
    """Simulate pass-through → markitdown → html-web-metadata → select-override."""
    stage_outputs: list[ExtractionStageOutput] = []

    pass_result = get_extractor("pass-through-text").extract_text(
        corpus=corpus,
        item=item,
        config={},
        previous_extractions=stage_outputs,
    )
    if pass_result is not None:
        stage_outputs.append(
            ExtractionStageOutput(
                stage_index=1,
                extractor_id="pass-through-text",
                status="extracted",
                text=pass_result.text,
                text_characters=len(pass_result.text or ""),
                producer_extractor_id=pass_result.producer_extractor_id,
                metadata=pass_result.metadata,
            )
        )

    md_result = ExtractedText(text=markitdown_text, producer_extractor_id="markitdown")
    stage_outputs.append(
        ExtractionStageOutput(
            stage_index=3,
            extractor_id="markitdown",
            status="extracted",
            text=md_result.text,
            text_characters=len(md_result.text),
            producer_extractor_id="markitdown",
        )
    )

    html_meta = HtmlWebMetadataExtractor().extract_text(
        corpus=corpus,
        item=item,
        config={},
        previous_extractions=stage_outputs,
    )
    assert html_meta is not None
    stage_outputs.append(
        ExtractionStageOutput(
            stage_index=4,
            extractor_id="html-web-metadata",
            status="extracted",
            text=html_meta.text,
            text_characters=len(html_meta.text or ""),
            producer_extractor_id=html_meta.producer_extractor_id,
            metadata=html_meta.metadata,
        )
    )

    final = SelectOverrideExtractor().extract_text(
        corpus=corpus,
        item=item,
        config={
            "media_type_patterns": ["text/html", "application/xhtml+xml"],
            "fallback_to_first": True,
        },
        previous_extractions=stage_outputs,
    )
    return final, stage_outputs


@pytest.fixture
def html_corpus(tmp_path: Path) -> tuple[Corpus, CatalogItem]:
    corpus = Corpus.init(tmp_path, force=True)
    html_bytes = _read("synthetic_blog_json_ld.html").encode("utf-8")
    ingest = corpus.ingest_item(
        html_bytes,
        filename="blog_post.html",
        media_type="text/html",
        tags=[],
        metadata={"sourceUri": "https://fixture.test/blog/post"},
        source_uri="https://fixture.test/blog/post",
    )
    catalog = corpus.load_catalog()
    item = catalog.items[ingest.item_id]
    return corpus, item


def test_recipe_includes_html_web_metadata_stage():
    recipe = yaml.safe_load(_RECIPE.read_text(encoding="utf-8"))
    stage_ids = [stage["extractor_id"] for stage in recipe["configuration"]["stages"]]
    assert "html-web-metadata" in stage_ids
    assert stage_ids.index("html-web-metadata") < stage_ids.index("select-override")
    assert stage_ids.index("markitdown") < stage_ids.index("html-web-metadata")


@pytest.mark.parametrize(
    "fixture_name,min_authors,min_citations",
    [
        ("synthetic_blog_json_ld.html", 2, 1),
        ("synthetic_news_open_graph.html", 1, 0),
        ("synthetic_references_only.html", 0, 1),
    ],
)
def test_html_web_metadata_fixtures(tmp_path: Path, fixture_name: str, min_authors: int, min_citations: int):
    corpus = Corpus.init(tmp_path, force=True)
    corpus.ingest_item(
        _read(fixture_name).encode("utf-8"),
        filename=fixture_name,
        media_type="text/html",
        tags=[],
        metadata=None,
        source_uri=f"https://fixture.test/{fixture_name}",
    )
    item = corpus.load_catalog().items[corpus.load_catalog().order[0]]
    final, _ = _run_pipeline_stages(
        corpus=corpus,
        item=item,
        markitdown_text="# Body\n\nConverted content for NER.",
    )
    assert final is not None
    assert is_grobid_extraction_metadata(final.metadata)
    structured = final.metadata["structured"]
    assert len(structured.get("authors") or []) >= min_authors
    assert len(structured.get("citations") or []) >= min_citations


def test_pipeline_select_override_carries_html_metadata(html_corpus: tuple[Corpus, CatalogItem]):
    corpus, item = html_corpus
    final, stages = _run_pipeline_stages(
        corpus=corpus,
        item=item,
        markitdown_text="# Sequence models\n\nArticle body mentioning Alex Example.",
    )
    assert final is not None
    assert final.metadata.get("method") == "html-heuristics"
    assert final.text != stages[0].text or "Sequence" in final.text
    html_stage = next(s for s in stages if s.extractor_id == "html-web-metadata")
    assert final.metadata == html_stage.metadata


def test_write_snapshot_metadata_roundtrip(html_corpus: tuple[Corpus, CatalogItem], tmp_path: Path):
    corpus, item = html_corpus
    final, _ = _run_pipeline_stages(
        corpus=corpus,
        item=item,
        markitdown_text="# Title\n\nContent.",
    )
    assert final is not None
    snap_dir = corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id="snap-html-test")
    snap_dir.mkdir(parents=True, exist_ok=True)
    relpath = extraction.write_extracted_metadata_artifact(
        snapshot_dir=snap_dir,
        item=item,
        metadata=final.metadata,
    )
    assert relpath is not None
    written = json.loads((snap_dir / relpath).read_text(encoding="utf-8"))
    assert written["method"] == "html-heuristics"
    assert is_grobid_extraction_metadata(written)


def test_graph_ner_suppresses_heuristic_authors_from_snapshot_metadata(
    html_corpus: tuple[Corpus, CatalogItem],
    monkeypatch: pytest.MonkeyPatch,
):
    corpus, item = html_corpus
    final, _ = _run_pipeline_stages(
        corpus=corpus,
        item=item,
        markitdown_text="Alex Example and Blair Sample discuss sequence models in this article.",
    )
    assert final is not None
    snap_dir = corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id="snap-ner")
    snap_dir.mkdir(parents=True, exist_ok=True)
    relpath = extraction.write_extracted_metadata_artifact(
        snapshot_dir=snap_dir,
        item=item,
        metadata=final.metadata,
    )
    extraction.write_extracted_text_artifact(
        snapshot_dir=snap_dir,
        item=item,
        text=final.text or "",
    )

    class _FakeEnt:
        def __init__(self, text: str, label: str) -> None:
            self.text = text
            self.label_ = label
            self.sent = type("S", (), {"start": 0})()

    class _FakeDoc:
        def __init__(self, ents) -> None:
            self.ents = ents

    def fake_nlp(_text: str):
        return _FakeDoc(
            [
                _FakeEnt("Alex Example", "PER"),
                _FakeEnt("Stanford University", "ORG"),
            ]
        )

    monkeypatch.setattr(ner_entities, "_load_spacy_pipeline", lambda _name: fake_nlp)

    loaded = json.loads((snap_dir / relpath).read_text(encoding="utf-8"))
    assert is_grobid_extraction_metadata(loaded)
    blocked = grobid_blocked_surface_forms(loaded["structured"])
    assert "alex example" in blocked

    entities = ner_entities._extract_entities(
        extracted_text=final.text or "",
        model_name="en",
        min_length=2,
        max_length=120,
        entity_labels=["PER", "ORG"],
        grobid_blocked_forms=blocked,
    )
    labels = {text for text, _label, _idx in entities}
    assert "Alex Example" not in labels
    assert "Stanford University" in labels


def test_build_extraction_snapshot_html_pipeline(
    html_corpus: tuple[Corpus, CatalogItem],
    monkeypatch: pytest.MonkeyPatch,
):
    corpus, item = html_corpus

    def fake_markitdown_extract(self, *, corpus, item, config, previous_extractions):
        return ExtractedText(
            text="# Understanding Sequence Models\n\nMarkdown body.",
            producer_extractor_id="markitdown",
        )

    monkeypatch.setattr(MarkItDownExtractor, "extract_text", fake_markitdown_extract)
    monkeypatch.delenv("AMPLIFY_AUTO_SYNC_CATALOG", raising=False)

    recipe = yaml.safe_load(_RECIPE.read_text(encoding="utf-8"))
    manifest = extraction.build_extraction_snapshot(
        corpus=corpus,
        extractor_id="pipeline",
        configuration_name="ai-ml-research-topic-text-test",
        configuration=recipe["configuration"],
        force=True,
        max_workers=1,
    )
    assert manifest.stats.get("extracted_items", 0) >= 1
    item_summary = next(row for row in manifest.items if row.item_id == item.id)
    assert item_summary.status == "extracted"
    assert item_summary.final_metadata_relpath

    snap_dir = corpus.extraction_snapshot_dir(
        extractor_id="pipeline",
        snapshot_id=manifest.snapshot_id,
    )
    meta_path = snap_dir / item_summary.final_metadata_relpath
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert payload.get("method") == "html-heuristics"
    assert is_grobid_extraction_metadata(payload)
    assert len(payload.get("structured", {}).get("authors") or []) >= 2


def test_html_web_metadata_returns_none_without_prior_text(tmp_path: Path):
    corpus = Corpus.init(tmp_path, force=True)
    corpus.ingest_item(
        b"<html><body>Hi</body></html>",
        filename="orphan.html",
        media_type="text/html",
        tags=[],
        metadata=None,
        source_uri="https://fixture.test/orphan",
    )
    item = corpus.load_catalog().items[corpus.load_catalog().order[0]]
    result = HtmlWebMetadataExtractor().extract_text(
        corpus=corpus,
        item=item,
        config={},
        previous_extractions=[],
    )
    assert result is None
