"""
Steering contract export commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..api import validate_request
from ..corpus import Corpus
from ..steering_proposals import (
    load_steering_proposal_bundle,
    record_steering_proposal_bundle,
)
from .common import (
    _add_common_corpus_arg,
    _corpus_path_from_arguments,
)


def cmd_steering_export(arguments: argparse.Namespace) -> int:
    """
    Export a stable steering bundle for an external application.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import SteeringExportRequest, steering_export

    request = validate_request(
        SteeringExportRequest,
        "steering export",
        corpus_path=_corpus_path_from_arguments(arguments),
        classifier_id=arguments.classifier,
        topic_governance_snapshot_id=arguments.topic_governance_snapshot,
    )
    print(steering_export(request).model_dump_json(indent=2))
    return 0


def cmd_steering_artifacts(arguments: argparse.Namespace) -> int:
    """
    List stable artifact references for an external steering worker.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import SteeringArtifactsRequest, steering_artifacts

    request = validate_request(
        SteeringArtifactsRequest,
        "steering artifacts",
        corpus_path=_corpus_path_from_arguments(arguments),
    )
    print(steering_artifacts(request).model_dump_json(indent=2))
    return 0


def cmd_steering_render_seed_manifest(arguments: argparse.Namespace) -> int:
    """
    Render an accepted steering topic set as a Biblicus seed manifest.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import SteeringRenderSeedManifestRequest, steering_render_seed_manifest

    request = validate_request(
        SteeringRenderSeedManifestRequest,
        "steering render-seed-manifest",
        input_path=arguments.input,
        output_path=arguments.output,
    )
    print(steering_render_seed_manifest(request).model_dump_json(indent=2))
    return 0


def cmd_steering_graph_signals(arguments: argparse.Namespace) -> int:
    """
    Emit topic-informed graph steering signals.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import SteeringGraphSignalsRequest, steering_graph_signals

    request = validate_request(
        SteeringGraphSignalsRequest,
        "steering graph-signals",
        corpus_path=_corpus_path_from_arguments(arguments),
        classifier_id=arguments.classifier,
        graph_snapshot=arguments.graph_snapshot,
        steering_feedback_path=arguments.steering_feedback,
    )
    print(steering_graph_signals(request).model_dump_json(indent=2))
    return 0


def cmd_steering_proposals_validate(arguments: argparse.Namespace) -> int:
    """
    Validate an externally authored steering proposal bundle.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    bundle = load_steering_proposal_bundle(Path(arguments.input))
    print(bundle.model_dump_json(indent=2))
    return 0


def cmd_steering_proposals_record(arguments: argparse.Namespace) -> int:
    """
    Record an externally authored steering proposal bundle.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = record_steering_proposal_bundle(
        corpus=corpus,
        input_path=Path(arguments.input),
    )
    print(output.model_dump_json(indent=2))
    return 0


def register_steering_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the steering commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_steering = subparsers.add_parser(
        "steering", help="Export Biblicus steering integration contracts."
    )
    steering_sub = p_steering.add_subparsers(dest="steering_command", required=True)

    p_steering_export = steering_sub.add_parser(
        "export", help="Emit a stable JSON bundle for external application import."
    )
    _add_common_corpus_arg(p_steering_export)
    p_steering_export.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier used to load the accepted topic set.",
    )
    p_steering_export.add_argument(
        "--topic-governance-snapshot",
        default=None,
        help="Topic governance snapshot identifier. Defaults to the latest pointer when omitted.",
    )
    p_steering_export.set_defaults(func=cmd_steering_export)

    p_steering_artifacts = steering_sub.add_parser(
        "artifacts", help="List stable Biblicus artifact references."
    )
    _add_common_corpus_arg(p_steering_artifacts)
    p_steering_artifacts.set_defaults(func=cmd_steering_artifacts)

    p_steering_graph_signals = steering_sub.add_parser(
        "graph-signals",
        help="Emit topic-informed graph steering signals.",
    )
    _add_common_corpus_arg(p_steering_graph_signals)
    p_steering_graph_signals.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier used to load accepted topics.",
    )
    p_steering_graph_signals.add_argument(
        "--graph-snapshot",
        required=True,
        help="Graph snapshot reference in extractor_id:snapshot_id form.",
    )
    p_steering_graph_signals.add_argument(
        "--steering-feedback",
        default=None,
        help="Papyrus steering feedback JSON with reviewed suppressions.",
    )
    p_steering_graph_signals.add_argument(
        "--format",
        choices=["json"],
        default="json",
        help="Output format.",
    )
    p_steering_graph_signals.set_defaults(func=cmd_steering_graph_signals)

    p_steering_proposals = steering_sub.add_parser(
        "proposals",
        help="Validate and record steering proposal bundles.",
    )
    steering_proposals_sub = p_steering_proposals.add_subparsers(
        dest="steering_proposals_command",
        required=True,
    )

    p_steering_proposals_validate = steering_proposals_sub.add_parser(
        "validate",
        help="Validate an externally authored steering proposal bundle.",
    )
    p_steering_proposals_validate.add_argument(
        "--input",
        required=True,
        help="Steering proposal bundle JSON input.",
    )
    p_steering_proposals_validate.set_defaults(func=cmd_steering_proposals_validate)

    p_steering_proposals_record = steering_proposals_sub.add_parser(
        "record",
        help="Record an externally authored steering proposal bundle.",
    )
    _add_common_corpus_arg(p_steering_proposals_record)
    p_steering_proposals_record.add_argument(
        "--input",
        required=True,
        help="Steering proposal bundle JSON input.",
    )
    p_steering_proposals_record.set_defaults(func=cmd_steering_proposals_record)

    p_steering_render = steering_sub.add_parser(
        "render-seed-manifest",
        help="Render an accepted steering topic set into a Biblicus seed manifest.",
    )
    p_steering_render.add_argument(
        "--input",
        required=True,
        help="Accepted steering topic-set JSON input.",
    )
    p_steering_render.add_argument(
        "--output",
        required=True,
        help="Destination Biblicus seed-manifest.json path.",
    )
    p_steering_render.set_defaults(func=cmd_steering_render_seed_manifest)
