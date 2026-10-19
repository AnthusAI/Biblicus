from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from biblicus import source_resolvers
from biblicus.corpus import Corpus
from biblicus.corpus_audit import (
    CorpusAuditDuplicateGroup,
    CorpusAuditDuplicateItem,
    CorpusAuditExtraction,
    CorpusAuditFacetCount,
    CorpusAuditFacets,
    CorpusAuditIssue,
    CorpusAuditOutput,
    CorpusAuditSummary,
    build_corpus_audit,
    corpus_audit_markdown,
)
from biblicus.extraction import build_extraction_snapshot
from biblicus.extractors import metadata_text, source_provided_text
from biblicus.extractors.metadata_text import MetadataTextExtractor, MetadataTextExtractorConfig
from biblicus.extractors.source_provided_text import (
    SourceProvidedTextExtractor,
    SourceProvidedTextExtractorConfig,
)
from biblicus.graph.reference_anchor import (
    build_reference_anchor_node,
    reference_title_blocked_forms,
    should_suppress_reference_title,
)
from biblicus.ingest_identity import canonical_ingest_identity_keys
from biblicus.models import CatalogItem
from biblicus.source_resolvers import (
    DocumentCloudResolver,
    ResolvedSource,
    resolve_source,
)


def _build_catalog_item(**overrides: Any) -> CatalogItem:
    payload: Dict[str, Any] = {
        "id": "item-1",
        "relpath": "raw/item.pdf",
        "sha256": "abc",
        "bytes": 1,
        "media_type": "application/pdf",
        "title": "Item Title",
        "tags": [],
        "metadata": {},
        "created_at": "now",
        "source_uri": None,
    }
    payload.update(overrides)
    return CatalogItem(**payload)


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exception_details: object) -> None:
        return None


def test_identity_keys_ignore_blank_source_and_missing_metadata() -> None:
    """Blank source URIs and absent metadata yield no identity keys."""
    assert canonical_ingest_identity_keys(source_uri="   ", metadata=None) == []
    assert canonical_ingest_identity_keys(source_uri=None, metadata={}) == []


def test_identity_keys_walk_nested_metadata_mappings_and_lists() -> None:
    """Identity values are collected from nested mappings and lists in metadata."""
    keys = canonical_ingest_identity_keys(
        source_uri=None,
        metadata={
            "discovery": {"nested": {"url": "https://arxiv.org/abs/2401.00001v2"}},
            "sources": [
                {"doi": "10.1000/abc"},
                [{"source_url": "https://www.documentcloud.org/documents/123-some-slug"}],
                "plain string is ignored",
            ],
            "source": {"deep": ["https://doi.org/10.2000/xyz", 7, {"k": "documentcloud:55"}]},
            "unrelated": "https://arxiv.org/abs/9999.99999",
            "numeric": 5,
        },
    )

    assert keys == [
        "arxiv:2401.00001",
        "doi:10.1000/abc",
        "doi:10.2000/xyz",
        "documentcloud:123",
        "documentcloud:55",
    ]


def test_identity_keys_reject_non_arxiv_http_hosts_and_unmatched_text() -> None:
    """Non-arXiv web hosts and text without identifiers produce no arXiv key."""
    unrelated_host_keys = canonical_ingest_identity_keys(
        source_uri="https://example.test/abs/2401.00001", metadata=None
    )
    plain_text_keys = canonical_ingest_identity_keys(
        source_uri="no identifiers here", metadata=None
    )

    assert unrelated_host_keys == []
    assert plain_text_keys == []


def test_identity_keys_documentcloud_url_forms() -> None:
    """DocumentCloud viewer, API, and asset hosts all normalize to one key shape."""
    api_keys = canonical_ingest_identity_keys(
        source_uri="https://api.www.documentcloud.org/api/documents/42/", metadata=None
    )
    asset_keys = canonical_ingest_identity_keys(
        source_uri="https://assets.documentcloud.org/documents/77/file.pdf", metadata=None
    )
    viewer_without_numeric_prefix = canonical_ingest_identity_keys(
        source_uri="https://www.documentcloud.org/documents/slug-only", metadata=None
    )
    api_without_numeric_id = canonical_ingest_identity_keys(
        source_uri="https://api.www.documentcloud.org/api/documents/abc/", metadata=None
    )
    asset_without_numeric_id = canonical_ingest_identity_keys(
        source_uri="https://assets.documentcloud.org/documents/abc/file.pdf", metadata=None
    )
    unrelated_host = canonical_ingest_identity_keys(
        source_uri="https://example.test/documents/12/file.pdf", metadata=None
    )

    assert api_keys == ["documentcloud:42"]
    assert asset_keys == ["documentcloud:77"]
    assert viewer_without_numeric_prefix == []
    assert api_without_numeric_id == []
    assert asset_without_numeric_id == []
    assert unrelated_host == []


def test_identity_keys_non_web_scheme_has_no_documentcloud_key() -> None:
    """Non-web schemes without an explicit documentcloud token are ignored."""
    assert canonical_ingest_identity_keys(source_uri="file:///tmp/a.pdf", metadata=None) == []


def test_resolved_source_requires_filename() -> None:
    """Resolved sources validate required text fields."""
    with pytest.raises(ValueError):
        ResolvedSource(data=b"x", filename="", media_type="a/b", source_uri="u")


def _documentcloud_document(**overrides: Any) -> Dict[str, Any]:
    document: Dict[str, Any] = {
        "id": 12,
        "status": "success",
        "access": "public",
        "slug": "report",
        "asset_url": "https://assets.documentcloud.org/",
        "canonical_url": "https://www.documentcloud.org/documents/12-report",
        "title": "Report",
        "file_hash": "hash",
        "language": "eng",
        "page_count": 3,
    }
    document.update(overrides)
    return document


def _install_documentcloud_loaders(
    monkeypatch: pytest.MonkeyPatch, document: Any, pdf_bytes: bytes = b"%PDF-1"
) -> list[str]:
    requested: list[str] = []

    def fake_load_json(url: str) -> Any:
        requested.append(url)
        return document

    def fake_load_bytes(url: str) -> bytes:
        requested.append(url)
        return pdf_bytes

    monkeypatch.setattr(source_resolvers, "_load_json", fake_load_json)
    monkeypatch.setattr(source_resolvers, "_load_bytes", fake_load_bytes)
    return requested


def test_documentcloud_resolver_resolves_public_document(monkeypatch: pytest.MonkeyPatch) -> None:
    """A public ready document resolves to its original PDF with resolution metadata."""
    requested = _install_documentcloud_loaders(monkeypatch, _documentcloud_document())
    resolver = DocumentCloudResolver(api_base_url="https://api.test/api", asset_base_url=None)

    resolved = resolver.resolve("https://www.documentcloud.org/documents/12-report")

    assert resolved.data == b"%PDF-1"
    assert resolved.filename == "report.pdf"
    assert resolved.title == "Report"
    assert resolved.source_uri == "https://www.documentcloud.org/documents/12-report"
    resolution = resolved.metadata["source_resolution"]
    assert resolution["identity_key"] == "documentcloud:12"
    assert resolution["raw_asset_uri"] == "https://assets.documentcloud.org/documents/12/report.pdf"
    assert resolution["derived_assets"]["full_text_uri"].endswith("/documents/12/report.txt")
    assert requested[0].startswith("https://api.test/api/documents/12/")


def test_documentcloud_resolver_uses_configured_asset_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configured asset base overrides the asset URL reported by the API."""
    _install_documentcloud_loaders(monkeypatch, _documentcloud_document(title=None))
    resolver = DocumentCloudResolver(
        api_base_url="https://api.test/api", asset_base_url="https://mirror.test/"
    )

    resolved = resolver.resolve("https://api.www.documentcloud.org/api/documents/12/")

    assert resolved.title is None
    assert resolved.metadata["source_resolution"]["raw_asset_uri"] == (
        "https://mirror.test/documents/12/report.pdf"
    )


@pytest.mark.parametrize(
    "document, message",
    [
        (["not", "an", "object"], "must be an object"),
        (_documentcloud_document(id=99), "does not match"),
        (_documentcloud_document(status="pending"), "not ready"),
        (_documentcloud_document(access="private"), "not public"),
        (_documentcloud_document(slug="  "), "missing required field: slug"),
        (_documentcloud_document(canonical_url=None), "missing required field: canonical_url"),
    ],
)
def test_documentcloud_resolver_rejects_invalid_documents(
    monkeypatch: pytest.MonkeyPatch, document: Any, message: str
) -> None:
    """Invalid DocumentCloud metadata responses raise clear errors."""
    _install_documentcloud_loaders(monkeypatch, document)
    resolver = DocumentCloudResolver(api_base_url="https://api.test/api", asset_base_url=None)

    with pytest.raises(ValueError, match=message):
        resolver.resolve("https://www.documentcloud.org/documents/12-report")


def test_documentcloud_resolver_rejects_unsupported_source() -> None:
    """Resolving a non-DocumentCloud source raises."""
    resolver = DocumentCloudResolver(api_base_url="https://api.test/api", asset_base_url=None)

    assert resolver.matches("https://example.test/a") is False
    with pytest.raises(ValueError, match="Unsupported DocumentCloud source"):
        resolver.resolve("https://example.test/a")


def test_resolve_source_dispatches_and_returns_none_for_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The registry resolves DocumentCloud sources and ignores other sources."""
    _install_documentcloud_loaders(monkeypatch, _documentcloud_document())

    resolved = resolve_source("https://assets.documentcloud.org/documents/12/report.pdf")

    assert resolved is not None
    assert resolved.media_type == "application/pdf"
    assert resolve_source("https://example.test/a") is None


def test_documentcloud_default_resolver_reads_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default resolver bases come from environment variables."""
    monkeypatch.setenv("BIBLICUS_DOCUMENTCLOUD_API_BASE", "https://env.test/api/")
    monkeypatch.setenv("BIBLICUS_DOCUMENTCLOUD_ASSET_BASE", "https://assets.env.test")

    resolver = DocumentCloudResolver()

    assert resolver.api_base_url == "https://env.test/api"
    assert resolver.asset_base_url == "https://assets.env.test"


def test_source_resolver_network_loaders_decode_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The JSON and byte loaders read from the opened response."""
    seen_urls: list[str] = []

    def fake_urlopen(request: Any, timeout: int) -> _FakeResponse:
        seen_urls.append(request.full_url)
        return _FakeResponse(json.dumps({"id": 1}).encode("utf-8"))

    monkeypatch.setattr(source_resolvers, "urlopen", fake_urlopen)

    assert source_resolvers._load_json("https://example.test/a") == {"id": 1}
    assert source_resolvers._load_bytes("https://example.test/b") == b'{"id": 1}'
    assert seen_urls == ["https://example.test/a", "https://example.test/b"]


def _extract_with_source_provided_text(metadata: Dict[str, Any]) -> Optional[Any]:
    extractor = SourceProvidedTextExtractor()
    config = extractor.validate_config({})
    assert isinstance(config, SourceProvidedTextExtractorConfig)
    return extractor.extract_text(
        corpus=None,
        item=_build_catalog_item(metadata=metadata),
        config=config,
        previous_extractions=[],
    )


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"source_resolution": "not-a-mapping"},
        {"source_resolution": {"derived_assets": ["not", "a", "mapping"]}},
        {"source_resolution": {"derived_assets": {"full_text_uri": "   "}}},
        {"source_resolution": {"derived_assets": {"full_text_uri": 5}}},
    ],
)
def test_source_provided_text_returns_none_without_usable_uri(metadata: Dict[str, Any]) -> None:
    """Items lacking a usable derived full text URI produce no extraction."""
    assert _extract_with_source_provided_text(metadata) is None


def test_source_provided_text_downloads_derived_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """The extractor downloads and returns source-provided full text."""
    requested: list[str] = []

    def fake_urlopen(request: Any, timeout: int) -> _FakeResponse:
        requested.append(request.full_url)
        return _FakeResponse("Full text body".encode("utf-8"))

    monkeypatch.setattr(source_provided_text, "urlopen", fake_urlopen)

    extracted = _extract_with_source_provided_text(
        {"source_resolution": {"derived_assets": {"full_text_uri": " https://example.test/t.txt "}}}
    )

    assert extracted is not None
    assert extracted.text == "Full text body"
    assert extracted.producer_extractor_id == "source-provided-text"
    assert extracted.metadata == {"source_provided_text_uri": "https://example.test/t.txt"}
    assert requested == ["https://example.test/t.txt"]


def test_reference_anchor_falls_back_to_relpath_label() -> None:
    """An untitled item labels its anchor with its relative path."""
    node = build_reference_anchor_node(_build_catalog_item(title=None))

    assert node.label == "raw/item.pdf"
    assert node.node_id == "reference:item-1"


def test_reference_title_suppression_ignores_blank_labels() -> None:
    """Blank labels are never suppressed and matching labels are."""
    assert should_suppress_reference_title("   ", {""}) is False
    assert should_suppress_reference_title(" ITEM TITLE ", {"item title"}) is True


def test_reference_title_blocked_forms_skip_blank_candidates() -> None:
    """Blank titles contribute nothing and extensions are stripped from paths."""
    blank_title = _build_catalog_item(title="   ", relpath="raw/Paper.HTML")
    extension_only = _build_catalog_item(title=".pdf", relpath="x.md")

    assert reference_title_blocked_forms(blank_title) == {"raw/paper.html", "raw/paper"}
    assert reference_title_blocked_forms(extension_only) == {".pdf", "x.md", "x"}


def test_reference_title_blocked_forms_ignore_missing_title() -> None:
    """An item without a title contributes only its relative path forms."""
    blocked = reference_title_blocked_forms(_build_catalog_item(title=None))

    assert blocked == {"raw/item.pdf", "raw/item"}


def _extract_metadata_text(item: CatalogItem, config: Dict[str, Any]) -> Optional[Any]:
    extractor = MetadataTextExtractor()
    return extractor.extract_text(
        corpus=None,
        item=item,
        config=extractor.validate_config(config),
        previous_extractions=[],
    )


def test_metadata_text_default_emits_title_and_tags() -> None:
    """Default configuration emits the title and a tags line."""
    extracted = _extract_metadata_text(
        _build_catalog_item(title=" Title ", tags=["a", " b ", ""]), {}
    )

    assert extracted is not None
    assert extracted.text == "Title\ntags: a, b"


def test_metadata_text_returns_none_without_metadata() -> None:
    """Items with no title or tags yield no extraction."""
    assert _extract_metadata_text(_build_catalog_item(title="  ", tags=[]), {}) is None


def test_metadata_text_selected_fields_render_each_value_kind() -> None:
    """Explicit fields render strings, lists, mappings, scalars and skip missing values."""
    item = _build_catalog_item(
        title="Paper",
        tags=["x", "y"],
        metadata={
            "abstract": "  Summary  ",
            "authors": ["Ada", " ", 3],
            "info": {"b": 1, "a": "é"},
            "count": 7,
            "blank": "   ",
            "empty": [],
        },
    )

    extracted = _extract_metadata_text(
        item,
        {
            "fields": [
                "title",
                "tags",
                "metadata.abstract",
                "metadata.authors",
                "metadata.info",
                "metadata.count",
                "metadata.blank",
                "metadata.empty",
                "metadata.absent",
            ]
        },
    )

    assert extracted is not None
    assert extracted.text.splitlines() == [
        "Paper",
        "x, y",
        "Summary",
        "Ada, 3",
        '{"a": "\\u00e9", "b": 1}',
        "7",
    ]


def test_metadata_text_selected_fields_with_no_values_return_none() -> None:
    """Selected fields that resolve to nothing produce no extraction."""
    assert _extract_metadata_text(_build_catalog_item(), {"fields": ["metadata.absent"]}) is None


def test_metadata_text_accepts_json_string_fields() -> None:
    """A JSON encoded field list is parsed by the configuration."""
    config = MetadataTextExtractorConfig.model_validate({"fields": '["title", "tags"]'})

    assert config.fields == ["title", "tags"]


@pytest.mark.parametrize(
    "fields, message",
    [
        ("not json", "list of field paths"),
        (["title", "  "], "non-empty"),
        (["unknown"], "title, tags, or metadata"),
    ],
)
def test_metadata_text_rejects_invalid_fields(fields: Any, message: str) -> None:
    """Invalid field specifications produce clear validation errors."""
    with pytest.raises(ValueError, match=message):
        MetadataTextExtractorConfig.model_validate({"fields": fields})


def test_metadata_text_accepts_unvalidated_configuration_mapping() -> None:
    """Extraction validates a raw mapping when handed one instead of a model."""
    extractor = MetadataTextExtractor()

    extracted = extractor.extract_text(
        corpus=None,
        item=_build_catalog_item(title="Raw"),
        config={"include_tags": False},
        previous_extractions=[],
    )

    assert extracted is not None
    assert extracted.text == "Raw"


def test_metadata_text_unknown_field_path_resolves_to_none() -> None:
    """Unrecognized field paths resolve to no value."""
    resolved = metadata_text._selected_field_value(item=_build_catalog_item(), field_path="zzz")

    assert resolved is None


def _ingest_audit_item(
    corpus: Corpus, *, body: bytes, title: str, source_uri: Optional[str], **kwargs: Any
) -> str:
    result = corpus.ingest_item(
        body,
        filename=f"{title or 'untitled'}.txt",
        media_type="text/plain",
        title=title,
        source_uri=source_uri,
        **kwargs,
    )
    return result.item_id


def test_corpus_audit_reports_legacy_metadata_and_source_domain_kinds(tmp_path: Path) -> None:
    """Audit flags legacy date metadata and classifies varied source URIs."""
    corpus = Corpus.init(tmp_path / "corpus")
    _ingest_audit_item(
        corpus,
        body=b"one",
        title="Legacy",
        source_uri="urn:test:legacy",
        tags=["t"],
        metadata={"published": "2020", "updated": "2021", "abstract": "A"},
    )
    _ingest_audit_item(corpus, body=b"two", title="", source_uri=None)
    _ingest_audit_item(
        corpus,
        body=b"three",
        title="Dated",
        source_uri="https://Example.test/x",
        tags=["t"],
        metadata={"dates": {"published_at": "n/a", "updated_at": "2021", "retrieved_at": "2022"}},
    )
    _ingest_audit_item(
        corpus,
        body=b"four",
        title="Plain",
        source_uri="no-scheme-at-all",
        tags=["t"],
        metadata={"dates": {"published_at": "2019-05-05"}},
    )

    audit = build_corpus_audit(corpus=corpus, required_tags=[" t ", ""], forbidden_tags=["zzz"])
    codes = [issue.code for issue in audit.issues]
    domains = {entry.value: entry.count for entry in audit.facets.source_domains}
    years = {entry.value for entry in audit.facets.publication_years}

    assert "legacy-published" in codes
    assert "legacy-updated" in codes
    assert "missing-title" in codes
    assert "missing-source-uri" in codes
    assert "empty-tags" in codes
    assert "missing-required-tag" in codes
    assert domains["missing"] == 1
    assert domains["urn"] == 1
    assert domains["example.test"] == 1
    assert domains["unknown"] == 1
    assert years == {"unknown", "2019"}
    assert audit.facets.missing_dates["updated_at"] == 3
    assert audit.facets.missing_dates["retrieved_at"] == 3


def test_corpus_audit_groups_duplicates_by_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Items sharing a canonical identity form duplicate groups."""
    monkeypatch.setattr(
        Corpus, "_raise_if_canonical_ingest_duplicate", lambda self, **keywords: None
    )
    corpus = Corpus.init(tmp_path / "corpus")
    _ingest_audit_item(
        corpus,
        body=b"beta",
        title="Beta",
        source_uri="https://arxiv.org/abs/2401.00001",
        tags=["t"],
        metadata={"doi": "10.1000/dup"},
    )
    _ingest_audit_item(
        corpus,
        body=b"gamma",
        title="Gamma",
        source_uri="https://arxiv.org/pdf/2401.00001",
        tags=["t"],
        metadata={"doi": "10.1000/dup"},
    )

    audit = build_corpus_audit(corpus=corpus)
    group_keys = {(group.key_type, group.key): group.count for group in audit.duplicates}

    assert group_keys[("canonical_identity", "doi:10.1000/dup")] == 2
    assert group_keys[("canonical_identity", "arxiv:2401.00001")] == 2
    assert all(count >= 2 for count in group_keys.values())


def test_corpus_audit_extraction_reports_non_extracted_and_empty_items(tmp_path: Path) -> None:
    """Extraction readiness lists skipped and whitespace-only extracted items."""
    corpus = Corpus.init(tmp_path / "corpus")
    blank_id = _ingest_audit_item(corpus, body=b"   \n", title="Blank", source_uri="urn:b")
    text_id = _ingest_audit_item(corpus, body=b"real text", title="Real", source_uri="urn:r")
    binary_result = corpus.ingest_item(
        b"\x00\x01binary",
        filename="data.bin",
        media_type="application/octet-stream",
        title="Binary",
        source_uri="urn:bin",
    )
    manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="audit-gaps",
        configuration={"stages": [{"extractor_id": "pass-through-text", "configuration": {}}]},
    )

    audit = build_corpus_audit(
        corpus=corpus, extraction_snapshot=f"pipeline:{manifest.snapshot_id}"
    )

    assert audit.extraction is not None
    assert text_id not in audit.extraction.empty_text_item_ids
    assert blank_id in audit.extraction.empty_text_item_ids
    assert binary_result.item_id in audit.extraction.non_extracted_item_ids
    assert audit.extraction.non_extracted_item_count == 1
    assert audit.extraction.empty_text_item_count == 1


def test_corpus_audit_extraction_rejects_missing_snapshot(tmp_path: Path) -> None:
    """A snapshot that does not exist raises a file error."""
    corpus = Corpus.init(tmp_path / "corpus")

    with pytest.raises(FileNotFoundError):
        build_corpus_audit(corpus=corpus, extraction_snapshot="pipeline:missing-snapshot")


def _build_populated_audit_output(with_extraction: bool) -> CorpusAuditOutput:
    extraction = None
    if with_extraction:
        extraction = CorpusAuditExtraction(
            snapshot="pipeline:snap",
            extractor_id="pipeline",
            snapshot_id="snap",
            catalog_generated_at="t1",
            snapshot_catalog_generated_at="t0",
            stale_catalog=True,
            total_items=3,
            covered_item_count=2,
            missing_item_count=1,
            non_extracted_item_count=1,
            empty_text_item_count=0,
        )
    return CorpusAuditOutput(
        summary=CorpusAuditSummary(
            corpus_uri="file:///corpus",
            catalog_generated_at="t1",
            item_count=3,
            total_bytes=30,
            latest_snapshot_id="retrieval-1",
        ),
        facets=CorpusAuditFacets(
            media_types=[CorpusAuditFacetCount(value="text/plain", count=3)],
            tags=[
                CorpusAuditFacetCount(value="a|b", count=2),
                CorpusAuditFacetCount(value="c", count=1),
            ],
            missing_dates={"published_at": 1},
        ),
        issues=[
            CorpusAuditIssue(
                code="missing-title", item_id="i1", title=None, detail="line one\nline two | x"
            )
        ],
        duplicates=[
            CorpusAuditDuplicateGroup(
                key_type="title",
                key="same",
                count=2,
                items=[
                    CorpusAuditDuplicateItem(item_id="i1", title="One"),
                    CorpusAuditDuplicateItem(item_id="i2"),
                ],
            )
        ],
        extraction=extraction,
    )


def test_corpus_audit_markdown_renders_issues_duplicates_and_extraction() -> None:
    """Markdown rendering escapes cells, truncates facets, and prints extraction facts."""
    markdown = corpus_audit_markdown(_build_populated_audit_output(True), top=1)

    assert "# Corpus Audit" in markdown
    assert "| a\\|b | 2 |" in markdown
    assert "| c | 1 |" not in markdown
    assert "| missing-title | i1 |  | line one line two \\| x |" in markdown
    assert "| title | same | 2 | One, i2 |" in markdown
    assert "- Stale catalog: true" in markdown
    assert "- Covered items: 2/3" in markdown
    assert markdown.endswith("\n")


def test_corpus_audit_markdown_renders_empty_sections() -> None:
    """Markdown rendering reports empty issues, duplicates, facets and unchecked extraction."""
    output = CorpusAuditOutput(
        summary=CorpusAuditSummary(
            corpus_uri="file:///corpus", catalog_generated_at="t", item_count=0, total_bytes=0
        ),
        facets=CorpusAuditFacets(),
    )

    markdown = corpus_audit_markdown(output, top=0)

    assert "No item issues found." in markdown
    assert "No duplicate signals found." in markdown
    assert "Not checked." in markdown
    assert "|  | 0 |" in markdown
