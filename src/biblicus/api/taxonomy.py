"""
Typed requests and functions for the ``taxonomy`` command group.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field

from .. import steering_feedback as steering_feedback_module
from .. import taxonomy as taxonomy_module
from ..models import ExtractionSnapshotReference
from ..taxonomy import TaxonomyDiscoveryOutput, TaxonomyRecordOutput
from ._common import ApiRequestModel, open_request_corpus


class TaxonomyRecordRequest(ApiRequestModel):
    """
    Request to record an accepted taxonomy manifest.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar input_path: Accepted taxonomy JSON input path.
    :vartype input_path: str
    """

    corpus_path: str = Field(min_length=1)
    input_path: str = Field(min_length=1)


class TaxonomyDiscoverRequest(ApiRequestModel):
    """
    Request to discover candidate child taxonomy nodes under accepted root topics.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar classifier_id: Topic classifier identifier used to collect root topic members.
    :vartype classifier_id: str
    :ivar extraction_snapshot: Extraction snapshot supplying item text.
    :vartype extraction_snapshot: ExtractionSnapshotReference
    :ivar steering_feedback_path: Optional reviewed steering feedback JSON path.
    :vartype steering_feedback_path: str or None
    """

    corpus_path: str = Field(min_length=1)
    classifier_id: str = Field(min_length=1)
    extraction_snapshot: ExtractionSnapshotReference
    steering_feedback_path: Optional[str] = Field(default=None, min_length=1)


def taxonomy_record(request: TaxonomyRecordRequest) -> TaxonomyRecordOutput:
    """
    Record an accepted taxonomy manifest.

    :param request: Validated request.
    :type request: TaxonomyRecordRequest
    :return: Recorded taxonomy snapshot description.
    :rtype: TaxonomyRecordOutput
    """
    return taxonomy_module.record_taxonomy_manifest(
        corpus=open_request_corpus(request.corpus_path),
        input_path=Path(request.input_path),
    )


def taxonomy_discover(request: TaxonomyDiscoverRequest) -> TaxonomyDiscoveryOutput:
    """
    Discover candidate child taxonomy nodes under accepted root topics.

    :param request: Validated request.
    :type request: TaxonomyDiscoverRequest
    :return: Discovery output.
    :rtype: TaxonomyDiscoveryOutput
    """
    steering_feedback = (
        steering_feedback_module.load_steering_feedback(Path(request.steering_feedback_path))
        if request.steering_feedback_path
        else None
    )
    return taxonomy_module.discover_taxonomy_children(
        corpus=open_request_corpus(request.corpus_path),
        classifier_id=request.classifier_id,
        extraction_snapshot=request.extraction_snapshot,
        steering_feedback=steering_feedback,
    )
