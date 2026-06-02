"""Tests for GROBID PDF text extraction fallback metadata."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from biblicus.extractors.grobid_pdf_text import GrobidPortableDocumentFormatTextExtractor
from biblicus.url_text import UrlTextExtractionError


def test_grobid_pdf_text_records_fallback_metadata(monkeypatch, tmp_path):
    extractor = GrobidPortableDocumentFormatTextExtractor()
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-fake")
    item = SimpleNamespace(
        id="pdf-1",
        relpath="paper.pdf",
        media_type="application/pdf",
    )
    corpus = SimpleNamespace(root=tmp_path)

    monkeypatch.setattr(
        "biblicus.extractors.grobid_pdf_text._convert_pdf_with_grobid",
        lambda **_kwargs: (_ for _ in ()).throw(
            UrlTextExtractionError(code="grobid_request_failed", message="down")
        ),
    )
    monkeypatch.setattr(
        "biblicus.extractors.grobid_pdf_text.PortableDocumentFormatTextExtractor.extract_text",
        lambda self, **_kwargs: SimpleNamespace(text="pypdf body", producer_extractor_id="pdf-text"),
    )

    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config={"fallback_to_pypdf": True, "record_fallback_metadata": True},
        previous_extractions=[],
    )
    assert result is not None
    assert result.producer_extractor_id == "grobid-pdf-text"
    assert result.metadata["method"] == "pypdf-fallback"
    assert result.metadata["grobid_fallback"]["code"] == "grobid_request_failed"


def test_grobid_pdf_text_raises_without_fallback(monkeypatch, tmp_path):
    extractor = GrobidPortableDocumentFormatTextExtractor()
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-fake")
    item = SimpleNamespace(
        id="pdf-1",
        relpath="paper.pdf",
        media_type="application/pdf",
    )
    corpus = SimpleNamespace(root=tmp_path)

    monkeypatch.setattr(
        "biblicus.extractors.grobid_pdf_text._convert_pdf_with_grobid",
        lambda **_kwargs: (_ for _ in ()).throw(
            UrlTextExtractionError(code="grobid_request_failed", message="down")
        ),
    )

    with pytest.raises(UrlTextExtractionError):
        extractor.extract_text(
            corpus=corpus,
            item=item,
            config={"fallback_to_pypdf": False},
            previous_extractions=[],
        )
