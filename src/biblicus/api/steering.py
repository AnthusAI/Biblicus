"""
Typed requests and functions for the ``steering`` command group.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field

from ..steering import (
    SteeringArtifactInventory,
    SteeringExportBundle,
    SteeringRenderSeedManifestOutput,
    build_steering_artifact_inventory,
    build_steering_export,
    render_steering_seed_manifest,
)
from ..steering_feedback import load_steering_feedback
from ..steering_proposals import SteeringProposalBundle, build_steering_graph_signal_bundle
from ._common import ApiRequestModel, open_request_corpus


class SteeringExportRequest(ApiRequestModel):
    """
    Request to export a stable steering bundle.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar classifier_id: Topic classifier identifier used to load the accepted topic set.
    :vartype classifier_id: str
    :ivar topic_governance_snapshot_id: Topic governance snapshot, or None for the latest pointer.
    :vartype topic_governance_snapshot_id: str or None
    """

    corpus_path: str = Field(min_length=1)
    classifier_id: str = Field(min_length=1)
    topic_governance_snapshot_id: Optional[str] = Field(default=None, min_length=1)


class SteeringArtifactsRequest(ApiRequestModel):
    """
    Request to list stable artifact references.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    """

    corpus_path: str = Field(min_length=1)


class SteeringGraphSignalsRequest(ApiRequestModel):
    """
    Request to emit topic-informed graph steering signals.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar classifier_id: Topic classifier identifier used to load accepted topics.
    :vartype classifier_id: str
    :ivar graph_snapshot: Graph snapshot reference in ``extractor_id:snapshot_id`` form.
    :vartype graph_snapshot: str
    :ivar steering_feedback_path: Optional reviewed steering feedback JSON path.
    :vartype steering_feedback_path: str or None
    """

    corpus_path: str = Field(min_length=1)
    classifier_id: str = Field(min_length=1)
    graph_snapshot: str = Field(min_length=1)
    steering_feedback_path: Optional[str] = Field(default=None, min_length=1)


class SteeringRenderSeedManifestRequest(ApiRequestModel):
    """
    Request to render an accepted steering topic set as a seed manifest.

    :ivar input_path: Accepted steering topic-set JSON input path.
    :vartype input_path: str
    :ivar output_path: Destination seed-manifest path.
    :vartype output_path: str
    """

    input_path: str = Field(min_length=1)
    output_path: str = Field(min_length=1)


def steering_export(request: SteeringExportRequest) -> SteeringExportBundle:
    """
    Export a stable steering bundle for an external application.

    :param request: Validated request.
    :type request: SteeringExportRequest
    :return: Steering export bundle.
    :rtype: SteeringExportBundle
    """
    return build_steering_export(
        corpus=open_request_corpus(request.corpus_path),
        classifier_id=request.classifier_id,
        topic_governance_snapshot_id=request.topic_governance_snapshot_id,
    )


def steering_artifacts(request: SteeringArtifactsRequest) -> SteeringArtifactInventory:
    """
    List stable artifact references for an external steering worker.

    :param request: Validated request.
    :type request: SteeringArtifactsRequest
    :return: Artifact inventory.
    :rtype: SteeringArtifactInventory
    """
    return build_steering_artifact_inventory(open_request_corpus(request.corpus_path))


def steering_graph_signals(request: SteeringGraphSignalsRequest) -> SteeringProposalBundle:
    """
    Emit topic-informed graph steering signals.

    :param request: Validated request.
    :type request: SteeringGraphSignalsRequest
    :return: Steering proposal bundle.
    :rtype: SteeringProposalBundle
    """
    steering_feedback = (
        load_steering_feedback(Path(request.steering_feedback_path))
        if request.steering_feedback_path
        else None
    )
    return build_steering_graph_signal_bundle(
        corpus=open_request_corpus(request.corpus_path),
        classifier_id=request.classifier_id,
        graph_snapshot=request.graph_snapshot,
        steering_feedback=steering_feedback,
    )


def steering_render_seed_manifest(
    request: SteeringRenderSeedManifestRequest,
) -> SteeringRenderSeedManifestOutput:
    """
    Render an accepted steering topic set as a Biblicus seed manifest.

    :param request: Validated request.
    :type request: SteeringRenderSeedManifestRequest
    :return: Description of the rendered manifest.
    :rtype: SteeringRenderSeedManifestOutput
    """
    return render_steering_seed_manifest(
        input_path=Path(request.input_path),
        output_path=Path(request.output_path),
    )
