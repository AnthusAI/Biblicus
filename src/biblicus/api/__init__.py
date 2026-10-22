"""
Typed Python application programming interface for the commands that Papyrus calls.

Each command has one Pydantic request model, one Pydantic response model and one plain function
that takes the request and returns the response. The command-line interface is a thin wrapper over
these functions and prints the response model as JSON. The :data:`API_COMMANDS` registry lists
every command so JSON Schemas can be generated and published.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, NamedTuple, Type

from pydantic import BaseModel

from ._common import (
    ApiRequestModel,
    ApiResponseModel,
    InvalidRequestError,
    format_validation_error,
    open_request_corpus,
    validate_request,
)
from .analysis import (
    TopicContextRequest,
    TopicIdentityRequest,
    TopicTrendsRequest,
    analyze_topic_context,
    analyze_topic_identity,
    analyze_topic_trends,
)
from .context_pack import (
    ContextPackBuildBlocksRequest,
    ContextPackBuildBlocksResponse,
    context_pack_build_blocks,
)
from .graph import GraphExtractRequest, graph_extract
from .retrieval import QueryRequest, ReindexRequest, ReindexResponse, query, reindex
from .steering import (
    SteeringArtifactsRequest,
    SteeringExportRequest,
    SteeringGraphSignalsRequest,
    SteeringRenderSeedManifestRequest,
    steering_artifacts,
    steering_export,
    steering_graph_signals,
    steering_render_seed_manifest,
)
from .taxonomy import (
    TaxonomyDiscoverRequest,
    TaxonomyRecordRequest,
    taxonomy_discover,
    taxonomy_record,
)
from .topic_classifier import (
    TopicClassifierProjectRequest,
    TopicClassifierTrainRequest,
    topic_classifier_project,
    topic_classifier_train,
)
from .web import (
    ArticleTextRequest,
    ArticleTextResponse,
    SummarizeMapReduceRequest,
    SummarizeMapReduceResponse,
    UrlTextFailureDetails,
    UrlTextRequest,
    UrlTextResponse,
    WebMetadataRequest,
    WebMetadataResponse,
    extract_article_text,
    extract_url_text,
    extract_web_metadata,
    summarize_map_reduce,
)


class ApiCommand(NamedTuple):
    """
    Registry entry tying a command to its request model, response model and function.

    :ivar name: Stable schema file stem, for example ``taxonomy-discover``.
    :vartype name: str
    :ivar group: Command-line group, for example ``taxonomy``.
    :vartype group: str
    :ivar request_model: Pydantic request model class.
    :vartype request_model: type[pydantic.BaseModel]
    :ivar response_model: Pydantic response model class.
    :vartype response_model: type[pydantic.BaseModel]
    :ivar function: Plain function taking the request and returning the response.
    :vartype function: collections.abc.Callable
    """

    name: str
    group: str
    request_model: Type[BaseModel]
    response_model: Type[BaseModel]
    function: Callable[..., Any]


def _registry_entries() -> Dict[str, ApiCommand]:
    from ..context import ContextBlockBuildRequest, ContextBlockBuildResult
    from ..graph.models import GraphSnapshotManifest
    from ..models import RetrievalResult
    from ..steering import (
        SteeringArtifactInventory,
        SteeringExportBundle,
        SteeringRenderSeedManifestOutput,
    )
    from ..steering_proposals import SteeringProposalBundle
    from ..taxonomy import TaxonomyDiscoveryOutput, TaxonomyRecordOutput
    from ..topic_classifier import TopicClassifierProjectionOutput, TopicClassifierTrainOutput
    from ..topic_context import TopicContextOutput
    from ..topic_identity import TopicIdentityOutput
    from ..topic_trends import TopicTrendOutput
    from ..web_transform import ArticleInput, TransformResult

    entries = [
        (
            "taxonomy-record",
            "taxonomy",
            TaxonomyRecordRequest,
            TaxonomyRecordOutput,
            taxonomy_record,
        ),
        (
            "taxonomy-discover",
            "taxonomy",
            TaxonomyDiscoverRequest,
            TaxonomyDiscoveryOutput,
            taxonomy_discover,
        ),
        (
            "steering-export",
            "steering",
            SteeringExportRequest,
            SteeringExportBundle,
            steering_export,
        ),
        (
            "steering-artifacts",
            "steering",
            SteeringArtifactsRequest,
            SteeringArtifactInventory,
            steering_artifacts,
        ),
        (
            "steering-graph-signals",
            "steering",
            SteeringGraphSignalsRequest,
            SteeringProposalBundle,
            steering_graph_signals,
        ),
        (
            "steering-render-seed-manifest",
            "steering",
            SteeringRenderSeedManifestRequest,
            SteeringRenderSeedManifestOutput,
            steering_render_seed_manifest,
        ),
        (
            "topic-classifier-train",
            "topic-classifier",
            TopicClassifierTrainRequest,
            TopicClassifierTrainOutput,
            topic_classifier_train,
        ),
        (
            "topic-classifier-project",
            "topic-classifier",
            TopicClassifierProjectRequest,
            TopicClassifierProjectionOutput,
            topic_classifier_project,
        ),
        (
            "analyze-topic-context",
            "analyze",
            TopicContextRequest,
            TopicContextOutput,
            analyze_topic_context,
        ),
        (
            "analyze-topic-trends",
            "analyze",
            TopicTrendsRequest,
            TopicTrendOutput,
            analyze_topic_trends,
        ),
        (
            "analyze-topic-identity",
            "analyze",
            TopicIdentityRequest,
            TopicIdentityOutput,
            analyze_topic_identity,
        ),
        (
            "context-pack-build-blocks",
            "context-pack",
            ContextBlockBuildRequest,
            ContextBlockBuildResult,
            context_pack_build_blocks,
        ),
        (
            "summarize-map-reduce",
            "summarize",
            SummarizeMapReduceRequest,
            TransformResult,
            summarize_map_reduce,
        ),
        ("extract-url-text", "extract", UrlTextRequest, UrlTextResponse, extract_url_text),
        (
            "extract-article-text",
            "extract",
            ArticleInput,
            TransformResult,
            extract_article_text,
        ),
        (
            "extract-web-metadata",
            "extract",
            WebMetadataRequest,
            WebMetadataResponse,
            extract_web_metadata,
        ),
        ("query", "query", QueryRequest, RetrievalResult, query),
        ("reindex", "reindex", ReindexRequest, ReindexResponse, reindex),
        ("graph-extract", "graph", GraphExtractRequest, GraphSnapshotManifest, graph_extract),
    ]
    return {name: ApiCommand(name, group, req, res, fn) for name, group, req, res, fn in entries}


API_COMMANDS: Dict[str, ApiCommand] = _registry_entries()


def build_api_schemas() -> Dict[str, Dict[str, Any]]:
    """
    Build the JSON Schema for every request and response model.

    Request schemas use validation mode and response schemas use serialization mode, so a response
    schema describes exactly the JSON the command prints.

    :return: Mapping of ``<command>.request`` and ``<command>.response`` to a JSON Schema object.
    :rtype: dict[str, dict[str, Any]]
    """
    schemas: Dict[str, Dict[str, Any]] = {}
    for command in API_COMMANDS.values():
        schemas[f"{command.name}.request"] = command.request_model.model_json_schema()
        schemas[f"{command.name}.response"] = command.response_model.model_json_schema(
            mode="serialization"
        )
    return schemas


__all__ = [
    "API_COMMANDS",
    "ApiCommand",
    "ApiRequestModel",
    "ApiResponseModel",
    "ArticleTextRequest",
    "ArticleTextResponse",
    "ContextPackBuildBlocksRequest",
    "ContextPackBuildBlocksResponse",
    "GraphExtractRequest",
    "QueryRequest",
    "ReindexRequest",
    "ReindexResponse",
    "SteeringArtifactsRequest",
    "SteeringExportRequest",
    "SteeringGraphSignalsRequest",
    "SteeringRenderSeedManifestRequest",
    "SummarizeMapReduceRequest",
    "SummarizeMapReduceResponse",
    "TaxonomyDiscoverRequest",
    "TaxonomyRecordRequest",
    "TopicClassifierProjectRequest",
    "TopicClassifierTrainRequest",
    "TopicContextRequest",
    "TopicIdentityRequest",
    "TopicTrendsRequest",
    "UrlTextRequest",
    "UrlTextFailureDetails",
    "UrlTextResponse",
    "WebMetadataRequest",
    "WebMetadataResponse",
    "analyze_topic_context",
    "analyze_topic_trends",
    "build_api_schemas",
    "context_pack_build_blocks",
    "extract_article_text",
    "extract_url_text",
    "extract_web_metadata",
    "InvalidRequestError",
    "format_validation_error",
    "graph_extract",
    "open_request_corpus",
    "query",
    "reindex",
    "steering_artifacts",
    "steering_export",
    "steering_graph_signals",
    "steering_render_seed_manifest",
    "summarize_map_reduce",
    "taxonomy_discover",
    "taxonomy_record",
    "topic_classifier_project",
    "topic_classifier_train",
    "validate_request",
]
