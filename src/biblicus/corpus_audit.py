"""
Read-only curation audit reporting for Biblicus corpora.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import DefaultDict, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from .corpus import Corpus
from .ingest_identity import canonical_ingest_identity_keys
from .models import CatalogItem, parse_extraction_snapshot_reference


class CorpusAuditFacetCount(BaseModel):
    """
    Count for one corpus audit facet value.

    :ivar value: Facet value.
    :vartype value: str
    :ivar count: Number of catalog items with this value.
    :vartype count: int
    """

    model_config = ConfigDict(extra="forbid")

    value: str
    count: int = Field(ge=0)


class CorpusAuditSummary(BaseModel):
    """
    Corpus-level inventory summary for a curation audit.

    :ivar corpus_uri: Canonical corpus uniform resource identifier.
    :vartype corpus_uri: str
    :ivar catalog_generated_at: Catalog generation timestamp.
    :vartype catalog_generated_at: str
    :ivar item_count: Number of catalog items.
    :vartype item_count: int
    :ivar total_bytes: Total raw item bytes.
    :vartype total_bytes: int
    :ivar latest_snapshot_id: Latest retrieval snapshot identifier, if present.
    :vartype latest_snapshot_id: str or None
    """

    model_config = ConfigDict(extra="forbid")

    corpus_uri: str
    catalog_generated_at: str
    item_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    latest_snapshot_id: Optional[str] = None


class CorpusAuditFacets(BaseModel):
    """
    Aggregated corpus facets for human curation.

    :ivar media_types: Counts by item media type.
    :vartype media_types: list[CorpusAuditFacetCount]
    :ivar tags: Counts by tag.
    :vartype tags: list[CorpusAuditFacetCount]
    :ivar source_domains: Counts by source domain or source scheme.
    :vartype source_domains: list[CorpusAuditFacetCount]
    :ivar publication_years: Counts by dates.published_at year.
    :vartype publication_years: list[CorpusAuditFacetCount]
    :ivar missing_dates: Counts of items missing canonical date fields.
    :vartype missing_dates: dict[str, int]
    """

    model_config = ConfigDict(extra="forbid")

    media_types: List[CorpusAuditFacetCount] = Field(default_factory=list)
    tags: List[CorpusAuditFacetCount] = Field(default_factory=list)
    source_domains: List[CorpusAuditFacetCount] = Field(default_factory=list)
    publication_years: List[CorpusAuditFacetCount] = Field(default_factory=list)
    missing_dates: Dict[str, int] = Field(default_factory=dict)


class CorpusAuditIssue(BaseModel):
    """
    Item-level corpus curation issue.

    :ivar code: Stable issue code.
    :vartype code: str
    :ivar item_id: Catalog item identifier.
    :vartype item_id: str
    :ivar title: Catalog item title, if present.
    :vartype title: str or None
    :ivar detail: Human-readable issue detail.
    :vartype detail: str
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    title: Optional[str] = None
    detail: str = Field(min_length=1)


class CorpusAuditDuplicateItem(BaseModel):
    """
    Item member of a duplicate-signal group.

    :ivar item_id: Catalog item identifier.
    :vartype item_id: str
    :ivar title: Catalog item title, if present.
    :vartype title: str or None
    :ivar source_uri: Source uniform resource identifier, if present.
    :vartype source_uri: str or None
    """

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    title: Optional[str] = None
    source_uri: Optional[str] = None


class CorpusAuditDuplicateGroup(BaseModel):
    """
    Duplicate-signal group in a corpus audit.

    :ivar key_type: Duplicate key kind.
    :vartype key_type: str
    :ivar key: Duplicate key value.
    :vartype key: str
    :ivar count: Number of grouped items.
    :vartype count: int
    :ivar items: Items sharing the duplicate key.
    :vartype items: list[CorpusAuditDuplicateItem]
    """

    model_config = ConfigDict(extra="forbid")

    key_type: str = Field(min_length=1)
    key: str = Field(min_length=1)
    count: int = Field(ge=2)
    items: List[CorpusAuditDuplicateItem] = Field(default_factory=list)


class CorpusAuditExtraction(BaseModel):
    """
    Extraction readiness comparison for a selected snapshot.

    :ivar snapshot: Extraction snapshot reference.
    :vartype snapshot: str
    :ivar extractor_id: Extraction plugin identifier.
    :vartype extractor_id: str
    :ivar snapshot_id: Extraction snapshot identifier.
    :vartype snapshot_id: str
    :ivar catalog_generated_at: Current catalog generation timestamp.
    :vartype catalog_generated_at: str
    :ivar snapshot_catalog_generated_at: Catalog timestamp recorded by the snapshot.
    :vartype snapshot_catalog_generated_at: str
    :ivar stale_catalog: Whether the selected snapshot was built from another catalog timestamp.
    :vartype stale_catalog: bool
    :ivar total_items: Current catalog item count.
    :vartype total_items: int
    :ivar covered_item_count: Number of catalog items represented in the snapshot.
    :vartype covered_item_count: int
    :ivar missing_item_count: Number of current catalog items absent from the snapshot.
    :vartype missing_item_count: int
    :ivar non_extracted_item_count: Number of represented items whose extraction status is not extracted.
    :vartype non_extracted_item_count: int
    :ivar empty_text_item_count: Number of represented extracted items with no non-whitespace text.
    :vartype empty_text_item_count: int
    :ivar missing_item_ids: Current catalog item identifiers absent from the snapshot.
    :vartype missing_item_ids: list[str]
    :ivar non_extracted_item_ids: Represented item identifiers not marked extracted.
    :vartype non_extracted_item_ids: list[str]
    :ivar empty_text_item_ids: Represented extracted item identifiers with no non-whitespace text.
    :vartype empty_text_item_ids: list[str]
    :ivar stats: Snapshot statistics.
    :vartype stats: dict[str, object]
    """

    model_config = ConfigDict(extra="forbid")

    snapshot: str = Field(min_length=1)
    extractor_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    catalog_generated_at: str = Field(min_length=1)
    snapshot_catalog_generated_at: str = Field(min_length=1)
    stale_catalog: bool
    total_items: int = Field(ge=0)
    covered_item_count: int = Field(ge=0)
    missing_item_count: int = Field(ge=0)
    non_extracted_item_count: int = Field(ge=0)
    empty_text_item_count: int = Field(ge=0)
    missing_item_ids: List[str] = Field(default_factory=list)
    non_extracted_item_ids: List[str] = Field(default_factory=list)
    empty_text_item_ids: List[str] = Field(default_factory=list)
    stats: Dict[str, object] = Field(default_factory=dict)


class CorpusAuditOutput(BaseModel):
    """
    Complete corpus curation audit output.

    :ivar summary: Corpus-level summary.
    :vartype summary: CorpusAuditSummary
    :ivar facets: Corpus-level facets.
    :vartype facets: CorpusAuditFacets
    :ivar issues: Item-level curation issues.
    :vartype issues: list[CorpusAuditIssue]
    :ivar duplicates: Duplicate-signal groups.
    :vartype duplicates: list[CorpusAuditDuplicateGroup]
    :ivar extraction: Optional extraction readiness comparison.
    :vartype extraction: CorpusAuditExtraction or None
    """

    model_config = ConfigDict(extra="forbid")

    summary: CorpusAuditSummary
    facets: CorpusAuditFacets
    issues: List[CorpusAuditIssue] = Field(default_factory=list)
    duplicates: List[CorpusAuditDuplicateGroup] = Field(default_factory=list)
    extraction: Optional[CorpusAuditExtraction] = None


def build_corpus_audit(
    *,
    corpus: Corpus,
    required_tags: Optional[Iterable[str]] = None,
    forbidden_tags: Optional[Iterable[str]] = None,
    extraction_snapshot: Optional[str] = None,
) -> CorpusAuditOutput:
    """
    Build a read-only curation audit from the current corpus catalog.

    :param corpus: Corpus to audit.
    :type corpus: Corpus
    :param required_tags: Tags every item is expected to contain.
    :type required_tags: iterable[str] or None
    :param forbidden_tags: Tags no item is expected to contain.
    :type forbidden_tags: iterable[str] or None
    :param extraction_snapshot: Optional extraction snapshot reference.
    :type extraction_snapshot: str or None
    :return: Corpus audit report.
    :rtype: CorpusAuditOutput
    :raises FileNotFoundError: If the requested extraction snapshot is missing.
    :raises ValueError: If the extraction snapshot reference is invalid.
    """
    catalog = corpus.load_catalog()
    items = list(catalog.items.values())
    required = sorted({tag.strip() for tag in required_tags or [] if tag.strip()})
    forbidden = sorted({tag.strip() for tag in forbidden_tags or [] if tag.strip()})
    summary = CorpusAuditSummary(
        corpus_uri=catalog.corpus_uri,
        catalog_generated_at=catalog.generated_at,
        item_count=len(items),
        total_bytes=sum(item.bytes for item in items),
        latest_snapshot_id=catalog.latest_snapshot_id,
    )
    audit = CorpusAuditOutput(
        summary=summary,
        facets=_build_facets(items),
        issues=_build_issues(items, required_tags=required, forbidden_tags=forbidden),
        duplicates=_build_duplicates(items),
    )
    if extraction_snapshot is not None:
        audit.extraction = _build_extraction_audit(
            corpus=corpus,
            extraction_snapshot=extraction_snapshot,
        )
    return audit


def corpus_audit_markdown(output: CorpusAuditOutput, *, top: int = 20) -> str:
    """
    Render a corpus audit as compact Markdown for curation review.

    :param output: Audit output to render.
    :type output: CorpusAuditOutput
    :param top: Maximum facet rows to render per facet.
    :type top: int
    :return: Markdown report.
    :rtype: str
    """
    row_limit = max(1, top)
    lines = [
        "# Corpus Audit",
        "",
        "## Summary",
        "",
        f"- Corpus: `{output.summary.corpus_uri}`",
        f"- Item count: {output.summary.item_count}",
        f"- Total bytes: {output.summary.total_bytes}",
        f"- Catalog generated at: {output.summary.catalog_generated_at}",
        f"- Latest retrieval snapshot: {output.summary.latest_snapshot_id or ''}",
        "",
        "## Facets",
        "",
    ]
    lines.extend(_facet_markdown("Media types", output.facets.media_types, top=row_limit))
    lines.extend(_facet_markdown("Tags", output.facets.tags, top=row_limit))
    lines.extend(_facet_markdown("Source domains", output.facets.source_domains, top=row_limit))
    lines.extend(
        _facet_markdown("Publication years", output.facets.publication_years, top=row_limit)
    )
    lines.append("### Missing Dates")
    lines.append("")
    lines.append("| field | missing |")
    lines.append("| --- | ---: |")
    for field_name, count in output.facets.missing_dates.items():
        lines.append(f"| `{field_name}` | {count} |")
    lines.extend(["", "## Issues", ""])
    if output.issues:
        lines.append("| code | item | title | detail |")
        lines.append("| --- | --- | --- | --- |")
        for issue in output.issues:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _markdown_cell(issue.code),
                        _markdown_cell(issue.item_id),
                        _markdown_cell(issue.title or ""),
                        _markdown_cell(issue.detail),
                    ]
                )
                + " |"
            )
    else:
        lines.append("No item issues found.")
    lines.extend(["", "## Duplicates", ""])
    if output.duplicates:
        lines.append("| key type | key | count | items |")
        lines.append("| --- | --- | ---: | --- |")
        for group in output.duplicates:
            item_titles = ", ".join(item.title or item.item_id for item in group.items)
            lines.append(
                "| "
                + " | ".join(
                    [
                        _markdown_cell(group.key_type),
                        _markdown_cell(group.key),
                        str(group.count),
                        _markdown_cell(item_titles),
                    ]
                )
                + " |"
            )
    else:
        lines.append("No duplicate signals found.")
    lines.extend(["", "## Extraction", ""])
    if output.extraction is None:
        lines.append("Not checked.")
    else:
        extraction = output.extraction
        lines.extend(
            [
                f"- Snapshot: `{extraction.snapshot}`",
                f"- Stale catalog: {str(extraction.stale_catalog).lower()}",
                f"- Covered items: {extraction.covered_item_count}/{extraction.total_items}",
                f"- Missing items: {extraction.missing_item_count}",
                f"- Non-extracted items: {extraction.non_extracted_item_count}",
                f"- Empty text items: {extraction.empty_text_item_count}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _build_facets(items: List[CatalogItem]) -> CorpusAuditFacets:
    media_types: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    source_domains: Counter[str] = Counter()
    publication_years: Counter[str] = Counter()
    missing_dates = {"published_at": 0, "updated_at": 0, "retrieved_at": 0}
    for item in items:
        media_types[item.media_type or ""] += 1
        for tag in item.tags:
            tags[tag] += 1
        source_domains[_source_domain(item.source_uri)] += 1
        dates = item.dates
        published_at = dates.published_at if dates is not None else None
        updated_at = dates.updated_at if dates is not None else None
        retrieved_at = dates.retrieved_at if dates is not None else None
        if published_at:
            publication_years[_publication_year(published_at)] += 1
        else:
            missing_dates["published_at"] += 1
        if not updated_at:
            missing_dates["updated_at"] += 1
        if not retrieved_at:
            missing_dates["retrieved_at"] += 1
    return CorpusAuditFacets(
        media_types=_counter_to_facets(media_types),
        tags=_counter_to_facets(tags),
        source_domains=_counter_to_facets(source_domains),
        publication_years=_counter_to_facets(publication_years),
        missing_dates=missing_dates,
    )


def _build_issues(
    items: List[CatalogItem], *, required_tags: List[str], forbidden_tags: List[str]
) -> List[CorpusAuditIssue]:
    issues: List[CorpusAuditIssue] = []
    for item in sorted(items, key=lambda entry: (entry.title or "", entry.id)):
        tags = set(item.tags)
        metadata = item.metadata or {}
        if not (item.title or "").strip():
            issues.append(_issue(item, code="missing-title", detail="Item has no title."))
        if not str(metadata.get("abstract") or "").strip():
            issues.append(_issue(item, code="missing-abstract", detail="Item has no abstract."))
        if item.dates is None or not (item.dates.published_at or "").strip():
            issues.append(
                _issue(
                    item,
                    code="missing-dates-published-at",
                    detail="Item has no dates.published_at value.",
                )
            )
        if not (item.source_uri or "").strip():
            issues.append(_issue(item, code="missing-source-uri", detail="Item has no source URI."))
        if not item.tags:
            issues.append(_issue(item, code="empty-tags", detail="Item has no tags."))
        for tag in required_tags:
            if tag not in tags:
                issues.append(
                    _issue(
                        item,
                        code="missing-required-tag",
                        detail=f"Item is missing required tag {tag}.",
                    )
                )
        for tag in forbidden_tags:
            if tag in tags:
                issues.append(
                    _issue(
                        item,
                        code="forbidden-tag",
                        detail=f"Item has forbidden tag {tag}.",
                    )
                )
        if "published" in metadata:
            issues.append(
                _issue(
                    item,
                    code="legacy-published",
                    detail="Item uses legacy top-level published metadata.",
                )
            )
        if "updated" in metadata:
            issues.append(
                _issue(
                    item,
                    code="legacy-updated",
                    detail="Item uses legacy top-level updated metadata.",
                )
            )
    return issues


def _build_duplicates(items: List[CatalogItem]) -> List[CorpusAuditDuplicateGroup]:
    groups: DefaultDict[tuple[str, str], List[CatalogItem]] = defaultdict(list)
    for item in items:
        normalized_title = _normalize_title(item.title)
        if normalized_title:
            groups[("title", normalized_title)].append(item)
        if item.source_uri:
            groups[("source_uri", item.source_uri)].append(item)
        if item.sha256:
            groups[("sha256", item.sha256)].append(item)
        for identity_key in canonical_ingest_identity_keys(
            source_uri=item.source_uri,
            metadata=item.metadata,
        ):
            groups[("canonical_identity", identity_key)].append(item)
    duplicates = []
    for (key_type, key), members in groups.items():
        unique_members = {member.id: member for member in members}
        if len(unique_members) < 2:
            continue
        ordered_members = sorted(
            unique_members.values(), key=lambda entry: (entry.title or "", entry.id)
        )
        duplicates.append(
            CorpusAuditDuplicateGroup(
                key_type=key_type,
                key=key,
                count=len(ordered_members),
                items=[
                    CorpusAuditDuplicateItem(
                        item_id=item.id,
                        title=item.title,
                        source_uri=item.source_uri,
                    )
                    for item in ordered_members
                ],
            )
        )
    duplicates.sort(key=lambda group: (group.key_type, group.key))
    return duplicates


def _build_extraction_audit(*, corpus: Corpus, extraction_snapshot: str) -> CorpusAuditExtraction:
    reference = parse_extraction_snapshot_reference(extraction_snapshot)
    catalog = corpus.load_catalog()
    manifest = corpus.load_extraction_snapshot_manifest(
        extractor_id=reference.extractor_id,
        snapshot_id=reference.snapshot_id,
    )
    catalog_item_ids = set(catalog.items)
    result_by_item_id = {item.item_id: item for item in manifest.items}
    represented_ids = set(result_by_item_id)
    missing_item_ids = sorted(catalog_item_ids - represented_ids)
    covered_ids = sorted(catalog_item_ids & represented_ids)
    non_extracted_item_ids = sorted(
        item_id for item_id in covered_ids if result_by_item_id[item_id].status != "extracted"
    )
    empty_text_item_ids = []
    for item_id in covered_ids:
        if result_by_item_id[item_id].status != "extracted":
            continue
        text = corpus.read_extracted_text(
            extractor_id=reference.extractor_id,
            snapshot_id=reference.snapshot_id,
            item_id=item_id,
        )
        if text is None or not text.strip():
            empty_text_item_ids.append(item_id)
    return CorpusAuditExtraction(
        snapshot=reference.as_string(),
        extractor_id=reference.extractor_id,
        snapshot_id=reference.snapshot_id,
        catalog_generated_at=catalog.generated_at,
        snapshot_catalog_generated_at=manifest.catalog_generated_at,
        stale_catalog=catalog.generated_at != manifest.catalog_generated_at,
        total_items=len(catalog_item_ids),
        covered_item_count=len(covered_ids),
        missing_item_count=len(missing_item_ids),
        non_extracted_item_count=len(non_extracted_item_ids),
        empty_text_item_count=len(empty_text_item_ids),
        missing_item_ids=missing_item_ids,
        non_extracted_item_ids=non_extracted_item_ids,
        empty_text_item_ids=empty_text_item_ids,
        stats=dict(manifest.stats),
    )


def _issue(item: CatalogItem, *, code: str, detail: str) -> CorpusAuditIssue:
    return CorpusAuditIssue(
        code=code,
        item_id=item.id,
        title=item.title,
        detail=detail,
    )


def _counter_to_facets(counter: Counter[str]) -> List[CorpusAuditFacetCount]:
    return [
        CorpusAuditFacetCount(value=value, count=count)
        for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _source_domain(source_uri: Optional[str]) -> str:
    if not source_uri:
        return "missing"
    parsed = urlparse(source_uri)
    if parsed.hostname:
        return parsed.hostname.lower()
    if parsed.scheme:
        return parsed.scheme.lower()
    return "unknown"


def _publication_year(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 4 and stripped[:4].isdigit():
        return stripped[:4]
    return "unknown"


def _normalize_title(title: Optional[str]) -> str:
    if not title:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", title.lower())
    return " ".join(normalized.split())


def _facet_markdown(title: str, entries: List[CorpusAuditFacetCount], *, top: int) -> List[str]:
    lines = [f"### {title}", "", "| value | count |", "| --- | ---: |"]
    for entry in entries[:top]:
        lines.append(f"| {_markdown_cell(entry.value)} | {entry.count} |")
    if not entries:
        lines.append("|  | 0 |")
    lines.append("")
    return lines


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
