"""
Typed requests and functions for the web extraction and bounded transform commands.

Covers ``extract url-text``, ``extract web-metadata``, ``extract article-text`` and
``summarize map-reduce``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, model_validator

from .. import url_text as url_text_module
from .. import web_reference_metadata as web_reference_metadata_module
from ..url_text import URL_TEXT_DEFAULT_TIMEOUT_SECONDS
from ..web_transform import ArticleInput, SourceInput, TransformResult, transform_source
from ._common import ApiRequestModel, ApiResponseModel


class UrlTextRequest(ApiRequestModel):
    """
    Request to extract readable text from a source URL.

    :ivar source_uri: Source URL.
    :vartype source_uri: str
    :ivar reference_title: Optional reference title context.
    :vartype reference_title: str
    :ivar timeout_seconds: Per-attempt fetch timeout in seconds.
    :vartype timeout_seconds: float
    """

    source_uri: str = Field(min_length=1)
    reference_title: str = ""
    timeout_seconds: float = Field(default=URL_TEXT_DEFAULT_TIMEOUT_SECONDS, gt=0)


class UrlTextResponse(ApiResponseModel):
    """
    Result of a URL text extraction.

    Fields that the extraction did not produce are absent from the serialized JSON, so a
    failed extraction omits ``method``, ``grobid`` and ``structured``.

    :ivar status: ``ok`` or ``failed``.
    :vartype status: str
    :ivar source_kind: ``web``, ``pdf`` or ``youtube``.
    :vartype source_kind: str
    :ivar strategy: Fetch strategy that was applied.
    :vartype strategy: str
    :ivar text: Extracted plain text.
    :vartype text: str
    :ivar markdown: Extracted markdown.
    :vartype markdown: str
    :ivar title: Extracted title or None.
    :vartype title: str or None
    :ivar content_type: Fetched content type or None.
    :vartype content_type: str or None
    :ivar method: Extraction method or None.
    :vartype method: str or None
    :ivar grobid: Scholarly parse payload or None.
    :vartype grobid: dict[str, Any] or None
    :ivar structured: Structured web payload or None.
    :vartype structured: dict[str, Any] or None
    :ivar prompt_version: Extraction contract version.
    :vartype prompt_version: str
    :ivar attempts: Ordered fetch attempts.
    :vartype attempts: list[dict[str, Any]]
    :ivar error: Structured failure or None.
    :vartype error: dict[str, Any] or None
    """

    status: Literal["ok", "failed"]
    source_kind: Literal["web", "pdf", "youtube"]
    strategy: str
    text: str
    markdown: str
    title: Optional[str]
    content_type: Optional[str]
    method: Optional[str] = None
    grobid: Optional[Dict[str, Any]] = None
    structured: Optional[Dict[str, Any]] = None
    prompt_version: str
    attempts: List[Dict[str, Any]]
    error: Optional[Dict[str, Any]]


class WebMetadataRequest(ApiRequestModel):
    """
    Request to extract reference metadata from a page URL or supplied HTML.

    :ivar source_uri: Page URL; fetched when ``html_content`` is absent.
    :vartype source_uri: str
    :ivar html_content: Supplied HTML document, which takes precedence over fetching.
    :vartype html_content: str
    :ivar reference_title: Optional title hint for model enrichment.
    :vartype reference_title: str
    :ivar use_llm_fallback: True to enrich sparse heuristics with a model.
    :vartype use_llm_fallback: bool
    :ivar model: Model identifier for enrichment.
    :vartype model: str
    :ivar timeout_seconds: Fetch timeout in seconds.
    :vartype timeout_seconds: float
    """

    source_uri: str = ""
    html_content: str = ""
    reference_title: str = ""
    use_llm_fallback: bool = False
    model: str = ""
    timeout_seconds: float = Field(default=URL_TEXT_DEFAULT_TIMEOUT_SECONDS, gt=0)

    @model_validator(mode="after")
    def require_source_uri_or_html_content(self) -> "WebMetadataRequest":
        """
        Require a page URL or supplied HTML.

        :return: The validated request.
        :rtype: WebMetadataRequest
        :raises ValueError: If both ``source_uri`` and ``html_content`` are blank.
        """
        if not self.source_uri.strip() and not self.html_content.strip():
            raise ValueError("Provide source_uri and/or html_content.")
        return self


class WebMetadataResponse(ApiResponseModel):
    """
    Reference metadata extracted from a web page.

    :ivar status: Always ``ok``; failures are raised as errors.
    :vartype status: str
    :ivar schemaVersion: Metadata contract version.
    :vartype schemaVersion: str
    :ivar sourceUri: Page URL used for provenance.
    :vartype sourceUri: str
    :ivar title: Page title or None.
    :vartype title: str or None
    :ivar subtitle: Page subtitle or None.
    :vartype subtitle: str or None
    :ivar authors: Author names.
    :vartype authors: list[str]
    :ivar authorsStructured: Structured author records.
    :vartype authorsStructured: list[dict[str, Any]]
    :ivar publicationDate: Normalized publication date or None.
    :vartype publicationDate: str or None
    :ivar publicationDateRaw: Publication date as found or None.
    :vartype publicationDateRaw: str or None
    :ivar updatedAt: Last update timestamp or None.
    :vartype updatedAt: str or None
    :ivar structured: Structured web payload.
    :vartype structured: dict[str, Any]
    :ivar method: Extraction method.
    :vartype method: str
    :ivar layers: Heuristic layers that contributed.
    :vartype layers: list[Any]
    :ivar rawMetadata: Raw page metadata.
    :vartype rawMetadata: dict[str, Any]
    :ivar warnings: Extraction warnings.
    :vartype warnings: list[Any]
    :ivar referenceCandidates: Candidate cited references.
    :vartype referenceCandidates: list[Any]
    :ivar citationCount: Number of structured citations.
    :vartype citationCount: int
    """

    status: Literal["ok"]
    schemaVersion: str
    sourceUri: str
    title: Optional[str]
    subtitle: Optional[str]
    authors: List[str]
    authorsStructured: List[Dict[str, Any]]
    publicationDate: Optional[str]
    publicationDateRaw: Optional[str]
    updatedAt: Optional[str]
    structured: Dict[str, Any]
    method: str
    layers: List[Any]
    rawMetadata: Dict[str, Any]
    warnings: List[Any]
    referenceCandidates: List[Any]
    citationCount: int


class SummarizeMapReduceRequest(SourceInput):
    """
    Request to map-reduce one bounded metadata field from extracted source text.

    :ivar task: Metadata field to generate.
    :vartype task: str
    :ivar model: Pinned model identifier.
    :vartype model: str
    """

    task: Literal["title", "subtitle", "summary"]
    model: str = Field(min_length=1)


ArticleTextRequest = ArticleInput
ArticleTextResponse = TransformResult
SummarizeMapReduceResponse = TransformResult


def extract_url_text(request: UrlTextRequest) -> UrlTextResponse:
    """
    Extract readable text from a source URL using the source-aware fetch strategy.

    :param request: Validated request.
    :type request: UrlTextRequest
    :return: Extraction result, with ``status`` ``failed`` and a structured error on failure.
    :rtype: UrlTextResponse
    """
    payload = url_text_module.extract_url_text(
        source_uri=request.source_uri,
        reference_title=request.reference_title,
        timeout_seconds=request.timeout_seconds,
    )
    return UrlTextResponse.model_validate(payload)


def extract_web_metadata(request: WebMetadataRequest) -> WebMetadataResponse:
    """
    Extract reference metadata from supplied HTML or a fetched page.

    :param request: Validated request.
    :type request: WebMetadataRequest
    :return: Reference metadata.
    :rtype: WebMetadataResponse
    :raises ValueError: If extraction rejects the supplied page.
    """
    source_uri = request.source_uri.strip()
    html_content = request.html_content.strip()
    if html_content:
        payload = web_reference_metadata_module.extract_web_reference_metadata_from_html(
            html_content,
            source_uri=source_uri or web_reference_metadata_module.LOCAL_HTML_SOURCE_URI,
            reference_title=request.reference_title,
            use_llm_fallback=request.use_llm_fallback,
            model=request.model,
        )
    else:
        payload = web_reference_metadata_module.extract_web_reference_metadata_from_url(
            source_uri,
            reference_title=request.reference_title,
            use_llm_fallback=request.use_llm_fallback,
            model=request.model,
            timeout_seconds=request.timeout_seconds,
        )
    return WebMetadataResponse.model_validate({"status": "ok", **payload})


def extract_article_text(request: ArticleTextRequest) -> ArticleTextResponse:
    """
    Select grounded article paragraphs from extracted source text.

    :param request: Validated article input.
    :type request: ArticleInput
    :return: Transform result, with ``status`` ``failed`` and a sanitized error on failure.
    :rtype: TransformResult
    """
    return transform_source(request, article=True, task=None, model=None)


def summarize_map_reduce(request: SummarizeMapReduceRequest) -> SummarizeMapReduceResponse:
    """
    Map source evidence and reduce one metadata field.

    :param request: Validated request.
    :type request: SummarizeMapReduceRequest
    :return: Transform result, with ``status`` ``failed`` and a sanitized error on failure.
    :rtype: TransformResult
    """
    source = SourceInput.model_validate(request.model_dump(exclude={"task", "model"}))
    return transform_source(source, article=False, task=request.task, model=request.model)
