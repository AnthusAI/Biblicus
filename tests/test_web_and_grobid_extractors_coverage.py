"""Coverage tests for the HTML web metadata and GROBID PDF text extractors."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from biblicus.extractors import grobid_pdf_text, html_web_metadata
from biblicus.extractors.grobid_pdf_text import (
    GrobidPortableDocumentFormatTextExtractor,
    GrobidPortableDocumentFormatTextExtractorConfig,
)
from biblicus.extractors.html_web_metadata import (
    HtmlWebMetadataExtractor,
    HtmlWebMetadataExtractorConfig,
    _latest_prior_producer,
    _latest_prior_text,
    _matches_html_media_type,
    _resolve_source_uri,
)
from biblicus.models import ExtractionStageOutput
from biblicus.url_text import UrlTextExtractionError

SIMPLE_ARTICLE_HTML = (
    "<html><head><title>Extractor Article</title></head>"
    "<body><article><p>Extractor body paragraph.</p></article></body></html>"
)


def _build_stage_output(*, stage_index, text, producer_extractor_id="markitdown"):
    return ExtractionStageOutput(
        stage_index=stage_index,
        extractor_id="markitdown",
        status="extracted",
        text=text,
        text_characters=len(text or ""),
        producer_extractor_id=producer_extractor_id,
    )


def _build_catalog_item(*, relpath, media_type, source_uri=None, metadata=None, title=""):
    return SimpleNamespace(
        id="item-1",
        relpath=relpath,
        media_type=media_type,
        title=title,
        source_uri=source_uri,
        metadata=metadata if metadata is not None else {},
    )


def test_html_web_metadata_validate_config_returns_model():
    """Verify that html web metadata validate config returns model."""
    parsed = HtmlWebMetadataExtractor().validate_config({"use_llm_fallback": True})
    assert isinstance(parsed, HtmlWebMetadataExtractorConfig)
    assert parsed.use_llm_fallback is True


def test_html_web_metadata_returns_none_without_prior_text(tmp_path):
    """Verify that html web metadata returns none without prior text."""
    result = HtmlWebMetadataExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=_build_catalog_item(relpath="page.html", media_type="text/html"),
        config=HtmlWebMetadataExtractorConfig(),
        previous_extractions=[_build_stage_output(stage_index=1, text="   ")],
    )
    assert result is None


def test_html_web_metadata_reports_unreadable_html_file(tmp_path):
    """Verify that html web metadata reports unreadable html file."""
    (tmp_path / "directory.html").mkdir()
    result = HtmlWebMetadataExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=_build_catalog_item(relpath="directory.html", media_type="text/html"),
        config={},
        previous_extractions=[_build_stage_output(stage_index=1, text="prior text")],
    )
    assert result.text == "prior text"
    assert result.producer_extractor_id == "html-web-metadata"
    assert result.metadata["method"] == "html_heuristics_unavailable"
    assert result.metadata["structured"]["warnings"][0]["code"] == "html_read_failed"


def test_html_web_metadata_uses_metadata_source_uri_and_llm_flag(monkeypatch, tmp_path):
    """Verify that html web metadata uses metadata source uri and llm flag."""
    (tmp_path / "page.html").write_text(SIMPLE_ARTICLE_HTML, encoding="utf-8")
    recorded_extraction_calls = []

    def fake_extract(html_body, **keyword_arguments):
        recorded_extraction_calls.append((html_body, keyword_arguments))
        return {"method": "html-heuristics", "title": "Extractor Article", "structured": {}}

    monkeypatch.setattr(html_web_metadata, "extract_web_reference_metadata_from_html", fake_extract)
    result = HtmlWebMetadataExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=_build_catalog_item(
            relpath="page.html",
            media_type="application/xhtml+xml",
            metadata={"url": "https://fixture.test/from-metadata"},
            title="Item Title",
        ),
        config=HtmlWebMetadataExtractorConfig(use_llm_fallback=True),
        previous_extractions=[
            _build_stage_output(stage_index=1, text="early", producer_extractor_id=None),
            _build_stage_output(stage_index=2, text="  "),
        ],
    )
    assert result.text == "early"
    assert result.producer_extractor_id == "markitdown"
    assert result.metadata["title"] == "Extractor Article"
    html_body, keyword_arguments = recorded_extraction_calls[0]
    assert html_body == SIMPLE_ARTICLE_HTML
    assert keyword_arguments == {
        "source_uri": "https://fixture.test/from-metadata",
        "reference_title": "Item Title",
        "use_llm_fallback": True,
    }


@pytest.mark.parametrize(
    ("media_type", "expected_match"),
    [("", False), (None, False), (" TEXT/HTML ", True), ("application/xhtml-variant", True)],
)
def test_matches_html_media_type_normalizes_media_type(media_type, expected_match):
    """Verify that matches html media type normalizes media type."""
    patterns = ["text/html", "application/XHTML*"]
    assert _matches_html_media_type(media_type, patterns) is expected_match


def test_latest_prior_text_and_producer_return_none_without_text():
    """Verify that latest prior text and producer return none without text."""
    assert _latest_prior_text([]) is None
    assert _latest_prior_producer([]) is None
    assert _latest_prior_producer([_build_stage_output(stage_index=1, text=" ")]) is None


def test_latest_prior_producer_prefers_latest_stage_with_text():
    """Verify that latest prior producer prefers latest stage with text."""
    stages = [
        _build_stage_output(stage_index=1, text="first", producer_extractor_id="first-producer"),
        _build_stage_output(stage_index=2, text="", producer_extractor_id="blank-producer"),
    ]
    assert _latest_prior_producer(stages) == "first-producer"


def test_resolve_source_uri_prefers_explicit_item_source_uri(tmp_path):
    """Verify that resolve source uri prefers explicit item source uri."""
    item = _build_catalog_item(
        relpath="page.html",
        media_type="text/html",
        source_uri=" https://fixture.test/explicit ",
        metadata={"url": "https://fixture.test/ignored"},
    )
    assert _resolve_source_uri(item, tmp_path / "page.html") == "https://fixture.test/explicit"


def test_resolve_source_uri_reads_first_non_empty_metadata_key(tmp_path):
    """Verify that resolve source uri reads first non empty metadata key."""
    item = _build_catalog_item(
        relpath="page.html",
        media_type="text/html",
        metadata={"source_uri": "  ", "canonicalUri": "https://fixture.test/canonical"},
    )
    assert _resolve_source_uri(item, tmp_path / "page.html") == "https://fixture.test/canonical"


def test_resolve_source_uri_falls_back_to_local_html_uri(tmp_path):
    """Verify that resolve source uri falls back to local html uri."""
    item = _build_catalog_item(relpath="page.html", media_type="text/html", metadata=None)
    item.metadata = "not-a-dict"
    assert (
        _resolve_source_uri(item, tmp_path / "page.html")
        == "https://papyrus.local/imported-html/page.html"
    )


def _write_fake_pdf(tmp_path):
    (tmp_path / "paper.pdf").write_bytes(b"%PDF-fake")
    return _build_catalog_item(relpath="paper.pdf", media_type="application/pdf")


def test_grobid_pdf_text_validate_config_returns_model():
    """Verify that grobid pdf text validate config returns model."""
    parsed = GrobidPortableDocumentFormatTextExtractor().validate_config({"max_pages": 3})
    assert isinstance(parsed, GrobidPortableDocumentFormatTextExtractorConfig)
    assert parsed.max_pages == 3


def test_grobid_pdf_text_skips_non_pdf_items(tmp_path):
    """Verify that grobid pdf text skips non pdf items."""
    result = GrobidPortableDocumentFormatTextExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=_build_catalog_item(relpath="page.html", media_type="text/html"),
        config={},
        previous_extractions=[],
    )
    assert result is None


def test_grobid_pdf_text_returns_grobid_text_and_metadata(monkeypatch, tmp_path):
    """Verify that grobid pdf text returns grobid text and metadata."""
    item = _write_fake_pdf(tmp_path)
    recorded_conversions = []

    def fake_convert(**keyword_arguments):
        recorded_conversions.append(keyword_arguments)
        return {
            "text": "  GROBID body  ",
            "title": "GROBID Title",
            "grobid": {"version": "0.8.0"},
            "structured": {"authors": [{"name": "Author"}]},
        }

    monkeypatch.setattr(grobid_pdf_text, "_convert_pdf_with_grobid", fake_convert)
    result = GrobidPortableDocumentFormatTextExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=item,
        config=GrobidPortableDocumentFormatTextExtractorConfig(),
        previous_extractions=[],
    )
    assert result.text == "GROBID body"
    assert result.metadata == {
        "method": "grobid",
        "grobid": {"version": "0.8.0"},
        "structured": {"authors": [{"name": "Author"}]},
        "title": "GROBID Title",
    }
    assert recorded_conversions[0]["data"] == b"%PDF-fake"
    assert recorded_conversions[0]["content_type"] == "application/pdf"


def test_grobid_pdf_text_normalizes_non_dict_grobid_fields(monkeypatch, tmp_path):
    """Verify that grobid pdf text normalizes non dict grobid fields."""
    item = _write_fake_pdf(tmp_path)
    monkeypatch.setattr(
        grobid_pdf_text,
        "_convert_pdf_with_grobid",
        lambda **_keyword_arguments: {"text": "body", "grobid": "x", "structured": "y"},
    )
    result = GrobidPortableDocumentFormatTextExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path), item=item, config={}, previous_extractions=[]
    )
    assert result.metadata["grobid"] == {}
    assert result.metadata["structured"] == {}
    assert result.metadata["title"] is None


def test_grobid_pdf_text_returns_none_for_empty_text_without_fallback(monkeypatch, tmp_path):
    """Verify that grobid pdf text returns none for empty text without fallback."""
    item = _write_fake_pdf(tmp_path)
    monkeypatch.setattr(
        grobid_pdf_text, "_convert_pdf_with_grobid", lambda **_keyword_arguments: {"text": "  "}
    )
    result = GrobidPortableDocumentFormatTextExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=item,
        config={"fallback_to_pypdf": False},
        previous_extractions=[],
    )
    assert result is None


def test_grobid_pdf_text_falls_back_for_empty_text_with_metadata(monkeypatch, tmp_path):
    """Verify that grobid pdf text falls back for empty text with metadata."""
    item = _write_fake_pdf(tmp_path)
    recorded_fallback_configs = []

    def fake_pypdf_extract(self, **keyword_arguments):
        recorded_fallback_configs.append(keyword_arguments["config"])
        return SimpleNamespace(text="pypdf body")

    monkeypatch.setattr(
        grobid_pdf_text, "_convert_pdf_with_grobid", lambda **_keyword_arguments: {"text": None}
    )
    monkeypatch.setattr(
        grobid_pdf_text.PortableDocumentFormatTextExtractor, "extract_text", fake_pypdf_extract
    )
    result = GrobidPortableDocumentFormatTextExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=item,
        config={"max_pages": 2},
        previous_extractions=[],
    )
    assert result.text == "pypdf body"
    assert result.metadata["method"] == "pypdf-fallback"
    assert result.metadata["grobid_fallback"] == {
        "reason": "grobid_empty_text",
        "code": "grobid_empty_text",
        "message": "GROBID returned no extractable body text.",
        "details": {},
    }
    assert result.metadata["structured"]["warnings"] == [
        {"code": "grobid_empty_text", "message": "GROBID returned no extractable body text."}
    ]
    assert recorded_fallback_configs[0].max_pages == 2


def _raise_grobid_unreachable(**_keyword_arguments):
    raise UrlTextExtractionError(
        code="grobid_unreachable", message="down", details={"url": "http://127.0.0.1:8070"}
    )


def test_grobid_pdf_text_fallback_returns_none_when_pypdf_returns_none(monkeypatch, tmp_path):
    """Verify that grobid pdf text fallback returns none when pypdf returns none."""
    item = _write_fake_pdf(tmp_path)
    monkeypatch.setattr(grobid_pdf_text, "_convert_pdf_with_grobid", _raise_grobid_unreachable)
    monkeypatch.setattr(
        grobid_pdf_text.PortableDocumentFormatTextExtractor,
        "extract_text",
        lambda self, **_keyword_arguments: None,
    )
    result = GrobidPortableDocumentFormatTextExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path), item=item, config={}, previous_extractions=[]
    )
    assert result is None


def test_grobid_pdf_text_fallback_without_recording_metadata(monkeypatch, tmp_path):
    """Verify that grobid pdf text fallback without recording metadata."""
    item = _write_fake_pdf(tmp_path)
    monkeypatch.setattr(grobid_pdf_text, "_convert_pdf_with_grobid", _raise_grobid_unreachable)
    monkeypatch.setattr(
        grobid_pdf_text.PortableDocumentFormatTextExtractor,
        "extract_text",
        lambda self, **_keyword_arguments: SimpleNamespace(text="pypdf body"),
    )
    result = GrobidPortableDocumentFormatTextExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=item,
        config={"record_fallback_metadata": False},
        previous_extractions=[],
    )
    assert result.text == "pypdf body"
    assert result.metadata == {}
    assert result.producer_extractor_id == "grobid-pdf-text"


def test_grobid_pdf_text_fallback_records_error_details(monkeypatch, tmp_path):
    """Verify that grobid pdf text fallback records error details."""
    item = _write_fake_pdf(tmp_path)
    monkeypatch.setattr(grobid_pdf_text, "_convert_pdf_with_grobid", _raise_grobid_unreachable)
    monkeypatch.setattr(
        grobid_pdf_text.PortableDocumentFormatTextExtractor,
        "extract_text",
        lambda self, **_keyword_arguments: SimpleNamespace(text="pypdf body"),
    )
    result = GrobidPortableDocumentFormatTextExtractor().extract_text(
        corpus=SimpleNamespace(root=tmp_path), item=item, config={}, previous_extractions=[]
    )
    assert result.metadata["grobid_fallback"]["reason"] == "grobid_error"
    assert result.metadata["grobid_fallback"]["details"] == {"url": "http://127.0.0.1:8070"}
