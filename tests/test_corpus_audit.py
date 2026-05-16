from __future__ import annotations

from pathlib import Path

from biblicus.corpus import Corpus
from biblicus.corpus_audit import build_corpus_audit
from biblicus.extraction import build_extraction_snapshot


def _ingest_article(
    corpus: Corpus,
    *,
    body: bytes,
    title: str,
    source_uri: str,
    tags: list[str] | None = None,
    published_at: str | None = None,
    abstract: str | None = "Article summary.",
) -> str:
    metadata: dict[str, object] = {}
    if abstract is not None:
        metadata["abstract"] = abstract
    if published_at is not None:
        metadata["dates"] = {"published_at": published_at}
    result = corpus.ingest_item(
        body,
        filename=f"{title}.html",
        media_type="text/html",
        title=title,
        tags=tags or [],
        metadata=metadata,
        source_uri=source_uri,
    )
    return result.item_id


def test_corpus_audit_aggregates_facets(tmp_path: Path) -> None:
    """Summarize catalog inventory into curation facets."""
    corpus = Corpus.init(tmp_path / "corpus")
    _ingest_article(
        corpus,
        body=b"<html>one</html>",
        title="One",
        source_uri="https://example.test/one",
        tags=["ai-ml-history", "article"],
        published_at="2020-01-02",
    )

    audit = build_corpus_audit(corpus=corpus)

    assert audit.summary.item_count == 1
    assert audit.facets.media_types[0].value == "text/html"
    assert audit.facets.tags[0].value == "ai-ml-history"
    assert audit.facets.source_domains[0].value == "example.test"
    assert audit.facets.publication_years[0].value == "2020"


def test_corpus_audit_reports_metadata_issues(tmp_path: Path) -> None:
    """Report item-level curation metadata gaps and tag policy violations."""
    corpus = Corpus.init(tmp_path / "corpus")
    _ingest_article(
        corpus,
        body=b"<html>undated</html>",
        title="Undated",
        source_uri="urn:test:undated",
        tags=["ai-ml-research"],
        abstract=None,
    )

    audit = build_corpus_audit(
        corpus=corpus,
        required_tags=["ai-ml-history"],
        forbidden_tags=["ai-ml-research"],
    )
    codes = {issue.code for issue in audit.issues}

    assert "missing-abstract" in codes
    assert "missing-dates-published-at" in codes
    assert "missing-required-tag" in codes
    assert "forbidden-tag" in codes


def test_corpus_audit_reports_duplicate_titles(tmp_path: Path) -> None:
    """Report duplicate-ish normalized titles without requiring exact titles."""
    corpus = Corpus.init(tmp_path / "corpus")
    _ingest_article(
        corpus,
        body=b"<html>one</html>",
        title="Same Thing",
        source_uri="urn:test:one",
        tags=["ai-ml-history"],
    )
    _ingest_article(
        corpus,
        body=b"<html>two</html>",
        title="same thing!",
        source_uri="urn:test:two",
        tags=["ai-ml-history"],
    )

    audit = build_corpus_audit(corpus=corpus)

    assert any(
        duplicate.key_type == "title" and duplicate.key == "same thing"
        for duplicate in audit.duplicates
    )


def test_corpus_audit_compares_extraction_snapshot(tmp_path: Path) -> None:
    """Compare a selected extraction snapshot against current catalog coverage."""
    corpus = Corpus.init(tmp_path / "corpus")
    _ingest_article(
        corpus,
        body=b"first",
        title="First",
        source_uri="urn:test:first",
        tags=["ai-ml-history"],
    )
    manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="audit-test",
        configuration={
            "stages": [
                {
                    "extractor_id": "pass-through-text",
                    "configuration": {},
                }
            ]
        },
    )

    current = build_corpus_audit(
        corpus=corpus,
        extraction_snapshot=f"pipeline:{manifest.snapshot_id}",
    )

    assert current.extraction is not None
    assert current.extraction.stale_catalog is False
    assert current.extraction.missing_item_count == 0

    _ingest_article(
        corpus,
        body=b"second",
        title="Second",
        source_uri="urn:test:second",
        tags=["ai-ml-history"],
    )
    stale = build_corpus_audit(
        corpus=corpus,
        extraction_snapshot=f"pipeline:{manifest.snapshot_id}",
    )

    assert stale.extraction is not None
    assert stale.extraction.stale_catalog is True
    assert stale.extraction.missing_item_count == 1
