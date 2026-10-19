"""Tests for HTML web metadata pipeline extractor."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from biblicus.extractors.html_web_metadata import HtmlWebMetadataExtractor
from biblicus.graph.grobid_dedup import is_grobid_extraction_metadata
from biblicus.models import ExtractionStageOutput
from biblicus.web_reference_metadata import extraction_metadata_from_web_payload

_FIXTURES = Path(__file__).parent / "fixtures" / "html_heuristics"


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_extraction_metadata_from_web_payload_shapes_graph_fields():
    metadata = extraction_metadata_from_web_payload(
        {
            "method": "html-heuristics",
            "title": "Example",
            "authors": ["Alex Example"],
            "structured": {"authors": [{"name": "Alex Example"}], "citations": [{"title": "Paper"}]},
            "layers": ["json_ld"],
        }
    )
    assert metadata["method"] == "html-heuristics"
    assert is_grobid_extraction_metadata(metadata)
    assert metadata["structured"]["authors"][0]["name"] == "Alex Example"


def test_html_web_metadata_skips_non_html(tmp_path):
    extractor = HtmlWebMetadataExtractor()
    item = SimpleNamespace(
        id="pdf-1",
        relpath="paper.pdf",
        media_type="application/pdf",
        title="",
        source_uri=None,
        metadata={},
    )
    corpus = SimpleNamespace(root=tmp_path)
    prior = ExtractionStageOutput(
        stage_index=2,
        extractor_id="markitdown",
        status="extracted",
        text="pdf body",
        text_characters=8,
        producer_extractor_id="markitdown",
    )
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config={},
        previous_extractions=[prior],
    )
    assert result is None


def test_html_web_metadata_attaches_structured_metadata(tmp_path):
    html_path = tmp_path / "article.html"
    html_path.write_text(_read("synthetic_blog_json_ld.html"), encoding="utf-8")
    extractor = HtmlWebMetadataExtractor()
    item = SimpleNamespace(
        id="html-1",
        relpath="article.html",
        media_type="text/html",
        title="",
        source_uri="https://fixture.test/blog/post",
        metadata={},
    )
    corpus = SimpleNamespace(root=tmp_path)
    prior = ExtractionStageOutput(
        stage_index=3,
        extractor_id="markitdown",
        status="extracted",
        text="# Markdown body from markitdown",
        text_characters=28,
        producer_extractor_id="markitdown",
    )
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config={},
        previous_extractions=[prior],
    )
    assert result is not None
    assert result.text == prior.text
    assert result.metadata["method"] == "html-heuristics"
    assert is_grobid_extraction_metadata(result.metadata)
    structured = result.metadata["structured"]
    assert len(structured.get("authors") or []) >= 2
    assert len(structured.get("citations") or []) >= 1
