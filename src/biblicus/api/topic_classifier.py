"""
Typed requests and functions for the ``topic-classifier`` command group.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import Field

from .. import topic_classifier as topic_classifier_module
from ..configuration import (
    apply_dotted_overrides,
    load_configuration_view,
    parse_dotted_overrides,
)
from ..corpus import Corpus
from ..models import ExtractionSnapshotReference
from ..topic_classifier import TopicClassifierProjectionOutput, TopicClassifierTrainOutput
from ._common import ApiRequestModel, open_request_corpus


class TopicClassifierTrainRequest(ApiRequestModel):
    """
    Request to train a topic classifier model version.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar manifest_path: Topic classifier seed manifest path.
    :vartype manifest_path: str
    :ivar configuration_paths: Configuration YAML paths; later files override earlier ones.
    :vartype configuration_paths: list[str]
    :ivar overrides: ``key=value`` overrides applied after composing configurations.
    :vartype overrides: list[str]
    :ivar configuration_name: Human-readable configuration name that keys the snapshot identity.
    :vartype configuration_name: str
    :ivar extraction_snapshot: Extraction snapshot supplying item text.
    :vartype extraction_snapshot: ExtractionSnapshotReference
    """

    corpus_path: str = Field(min_length=1)
    manifest_path: str = Field(min_length=1)
    configuration_paths: List[str] = Field(min_length=1)
    overrides: List[str] = Field(default_factory=list)
    configuration_name: str = Field(default="default", min_length=1)
    extraction_snapshot: ExtractionSnapshotReference


class TopicClassifierProjectRequest(ApiRequestModel):
    """
    Request to project a classifier from an authority corpus onto a target corpus.

    :ivar classifier_corpus_path: Corpus path holding classifier artifacts.
    :vartype classifier_corpus_path: str
    :ivar target_corpus_path: Corpus path holding the items to classify.
    :vartype target_corpus_path: str
    :ivar classifier_id: Topic classifier identifier.
    :vartype classifier_id: str
    :ivar extraction_snapshot: Target corpus extraction snapshot.
    :vartype extraction_snapshot: ExtractionSnapshotReference
    :ivar project_all: True to project onto every target item.
    :vartype project_all: bool
    :ivar item_ids: Target item identifiers to project.
    :vartype item_ids: list[str]
    :ivar review_threshold: Minimum confidence before review is recommended.
    :vartype review_threshold: float
    :ivar top_k: Maximum ranked topic candidates to include.
    :vartype top_k: int
    :ivar record: True to persist projection predictions as audit records.
    :vartype record: bool
    """

    classifier_corpus_path: str = Field(min_length=1)
    target_corpus_path: str = Field(min_length=1)
    classifier_id: str = Field(min_length=1)
    extraction_snapshot: ExtractionSnapshotReference
    project_all: bool = False
    item_ids: List[str] = Field(default_factory=list)
    review_threshold: float = 0.35
    top_k: int = Field(default=5, ge=1)
    record: bool = False


def topic_classifier_train(request: TopicClassifierTrainRequest) -> TopicClassifierTrainOutput:
    """
    Train a topic classifier model version.

    :param request: Validated request.
    :type request: TopicClassifierTrainRequest
    :return: Training output.
    :rtype: TopicClassifierTrainOutput
    """
    corpus = open_request_corpus(request.corpus_path)
    configuration_data = load_configuration_view(
        request.configuration_paths,
        configuration_label="Topic classifier configuration",
        mapping_error_message="Topic classifier configuration must be a mapping/object",
    )
    configuration_data = apply_dotted_overrides(
        configuration_data, parse_dotted_overrides(request.overrides)
    )
    return topic_classifier_module.train_topic_classifier(
        corpus=corpus,
        manifest_path=Path(request.manifest_path).resolve(),
        configuration_name=request.configuration_name,
        configuration=configuration_data,
        extraction_snapshot=request.extraction_snapshot,
    )


def topic_classifier_project(
    request: TopicClassifierProjectRequest,
) -> TopicClassifierProjectionOutput:
    """
    Project a topic classifier from an authority corpus onto a target corpus.

    :param request: Validated request.
    :type request: TopicClassifierProjectRequest
    :return: Projection output.
    :rtype: TopicClassifierProjectionOutput
    """
    return topic_classifier_module.project_topic_classifier_items(
        classifier_corpus=Corpus.open(request.classifier_corpus_path),
        target_corpus=Corpus.open(request.target_corpus_path),
        classifier_id=request.classifier_id,
        extraction_snapshot=request.extraction_snapshot,
        project_all=request.project_all,
        item_ids=request.item_ids,
        review_threshold=request.review_threshold,
        top_k=request.top_k,
        record=request.record,
    )
