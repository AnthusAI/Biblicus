"""
Typed requests and functions for the ``analyze topic-context`` and ``analyze topic-trends`` commands.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from .. import topic_context as topic_context_module
from .. import topic_trends as topic_trends_module
from ..topic_context import TopicContextOutput
from ..topic_trends import TopicTrendOutput
from ._common import ApiRequestModel, open_request_corpus


class TopicContextRequest(ApiRequestModel):
    """
    Request to generate a research-agent topic context report.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar topic_modeling_snapshot_id: Topic modeling snapshot to summarize.
    :vartype topic_modeling_snapshot_id: str
    :ivar max_topics: Maximum non-outlier topic buckets to include.
    :vartype max_topics: int
    :ivar examples_per_topic: Maximum representative examples per topic.
    :vartype examples_per_topic: int
    :ivar summary_model: Optional model for topic guidance and missing example summaries.
    :vartype summary_model: str or None
    :ivar include_outlier: True to include the outlier topic.
    :vartype include_outlier: bool
    """

    corpus_path: str = Field(min_length=1)
    topic_modeling_snapshot_id: str = Field(min_length=1)
    max_topics: int = Field(default=20, ge=1)
    examples_per_topic: int = Field(default=3, ge=1)
    summary_model: Optional[str] = Field(default=None, min_length=1)
    include_outlier: bool = False


class TopicTrendsRequest(ApiRequestModel):
    """
    Request to run publication-date topic trend analysis.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar topic_modeling_snapshot_id: Topic modeling snapshot to analyze.
    :vartype topic_modeling_snapshot_id: str
    :ivar classifier_id: Optional topic classifier for canonical topic coverage.
    :vartype classifier_id: str or None
    :ivar windows: Publication windows such as ``30d``, ``90d``, ``1y``, ``all``.
    :vartype windows: list[str]
    :ivar as_of: Publication date anchor, or None for the latest published date.
    :vartype as_of: str or None
    :ivar rank_window: Window used to rank topics; must be one of ``windows``.
    :vartype rank_window: str
    """

    corpus_path: str = Field(min_length=1)
    topic_modeling_snapshot_id: str = Field(min_length=1)
    classifier_id: Optional[str] = Field(default=None, min_length=1)
    windows: List[str] = Field(default_factory=lambda: ["30d", "90d", "1y", "all"], min_length=1)
    as_of: Optional[str] = Field(default=None, min_length=1)
    rank_window: str = Field(default="90d", min_length=1)


def analyze_topic_context(request: TopicContextRequest) -> TopicContextOutput:
    """
    Generate a research-agent topic context report.

    :param request: Validated request.
    :type request: TopicContextRequest
    :return: Topic context report.
    :rtype: TopicContextOutput
    """
    return topic_context_module.build_topic_context(
        corpus=open_request_corpus(request.corpus_path),
        topic_modeling_snapshot_id=request.topic_modeling_snapshot_id,
        max_topics=request.max_topics,
        examples_per_topic=request.examples_per_topic,
        summary_model=request.summary_model,
        include_outlier=request.include_outlier,
    )


def analyze_topic_trends(request: TopicTrendsRequest) -> TopicTrendOutput:
    """
    Run publication-date topic trend analysis.

    :param request: Validated request.
    :type request: TopicTrendsRequest
    :return: Topic trend report.
    :rtype: TopicTrendOutput
    """
    return topic_trends_module.build_topic_trends(
        corpus=open_request_corpus(request.corpus_path),
        topic_modeling_snapshot_id=request.topic_modeling_snapshot_id,
        classifier_id=request.classifier_id,
        windows=request.windows,
        as_of=request.as_of,
        rank_window=request.rank_window,
    )
