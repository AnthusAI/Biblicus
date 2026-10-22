"""
Typed requests and functions for the ``analyze topic-context``, ``analyze topic-trends`` and ``analyze topic-identity`` commands.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field, model_validator

from .. import topic_context as topic_context_module
from .. import topic_identity as topic_identity_module
from .. import topic_trends as topic_trends_module
from ..topic_context import TopicContextOutput
from ..topic_identity import TopicIdentityOutput
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
    :ivar bin: ``weekly`` to add weekly counts per topic, or None for the trailing windows only.
    :vartype bin: str or None
    :ivar weeks: Number of weekly bins, 8 when omitted. Requires ``bin``.
    :vartype weeks: int or None
    """

    corpus_path: str = Field(min_length=1)
    topic_modeling_snapshot_id: str = Field(min_length=1)
    classifier_id: Optional[str] = Field(default=None, min_length=1)
    windows: List[str] = Field(default_factory=lambda: ["30d", "90d", "1y", "all"], min_length=1)
    as_of: Optional[str] = Field(default=None, min_length=1)
    rank_window: str = Field(default="90d", min_length=1)
    bin: Optional[Literal["weekly"]] = None
    weeks: Optional[int] = Field(default=None, ge=1, le=520)

    @model_validator(mode="after")
    def _weeks_requires_bin(self) -> "TopicTrendsRequest":
        if self.weeks is not None and self.bin is None:
            raise ValueError("weeks requires bin")
        return self


class TopicIdentityRequest(ApiRequestModel):
    """
    Request to match topic-model clusters to the previous run and assign stable identifiers.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar current_run_id: Topic modeling snapshot to identify.
    :vartype current_run_id: str
    :ivar previous_run_id: Previous topic modeling snapshot, or None for the first run.
    :vartype previous_run_id: str or None
    :ivar threshold: Minimum Jaccard overlap of member item identifiers for a match.
    :vartype threshold: float
    :ivar trends_snapshot_id: Topic trends snapshot with weekly bins for the eight-week series.
    :vartype trends_snapshot_id: str or None
    """

    corpus_path: str = Field(min_length=1)
    current_run_id: str = Field(min_length=1)
    previous_run_id: Optional[str] = Field(default=None, min_length=1)
    threshold: float = Field(default=0.5, gt=0, le=1)
    trends_snapshot_id: Optional[str] = Field(default=None, min_length=1)


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
        bin=request.bin,
        weeks=request.weeks,
    )


def analyze_topic_identity(request: TopicIdentityRequest) -> TopicIdentityOutput:
    """
    Assign stable cluster identifiers and lifecycle events to a topic modeling run.

    :param request: Validated request.
    :type request: TopicIdentityRequest
    :return: Cluster identity report.
    :rtype: TopicIdentityOutput
    """
    return topic_identity_module.build_topic_identity(
        corpus=open_request_corpus(request.corpus_path),
        current_run_id=request.current_run_id,
        previous_run_id=request.previous_run_id,
        threshold=request.threshold,
        trends_snapshot_id=request.trends_snapshot_id,
    )
