"""
Taxonomy and ontology commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..api import validate_request
from ..corpus import Corpus
from .common import (
    _add_common_corpus_arg,
    _corpus_path_from_arguments,
    _open_corpus_from_arguments,
    _resolve_extraction_snapshot_for_analysis,
)


def cmd_taxonomy_record(arguments: argparse.Namespace) -> int:
    """
    Record an accepted taxonomy manifest.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import TaxonomyRecordRequest, taxonomy_record

    request = validate_request(
        TaxonomyRecordRequest,
        "taxonomy record",
        corpus_path=_corpus_path_from_arguments(arguments),
        input_path=arguments.input,
    )
    print(taxonomy_record(request).model_dump_json(indent=2))
    return 0


def cmd_taxonomy_discover(arguments: argparse.Namespace) -> int:
    """
    Discover candidate child taxonomy nodes under accepted root topics.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import TaxonomyDiscoverRequest, taxonomy_discover
    from ..taxonomy import taxonomy_discovery_markdown

    corpus = _open_corpus_from_arguments(arguments)
    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Taxonomy discovery",
    )
    request = validate_request(
        TaxonomyDiscoverRequest,
        "taxonomy discover",
        corpus_path=str(corpus.root),
        classifier_id=arguments.classifier,
        extraction_snapshot=extraction_snapshot,
        steering_feedback_path=arguments.steering_feedback,
    )
    output = taxonomy_discover(request)
    if arguments.format == "markdown":
        print(taxonomy_discovery_markdown(output))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_ontology_record(arguments: argparse.Namespace) -> int:
    """
    Record an accepted ontology manifest.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..ontology import record_ontology_manifest

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = record_ontology_manifest(corpus=corpus, input_path=Path(arguments.input))
    print(output.model_dump_json(indent=2))
    return 0


def cmd_ontology_apply(arguments: argparse.Namespace) -> int:
    """
    Apply accepted taxonomy and ontology assertions to a graph snapshot.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..ontology import apply_ontology_to_graph

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = apply_ontology_to_graph(
        corpus=corpus,
        taxonomy_snapshot_id=arguments.taxonomy,
        ontology_snapshot_id=arguments.relationships,
        graph_snapshot=arguments.graph_snapshot,
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_ontology_query(arguments: argparse.Namespace) -> int:
    """
    Query accepted ontology assertions.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..ontology import query_ontology_assertions

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = query_ontology_assertions(
        corpus=corpus,
        ontology_snapshot_id=arguments.relationships,
        source_ref=arguments.source_ref,
        relationship_uid=arguments.relationship,
        direction=arguments.direction,
    )
    print(output.model_dump_json(indent=2))
    return 0


def register_taxonomy_ontology_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the taxonomy ontology commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_taxonomy = subparsers.add_parser(
        "taxonomy", help="Validate and discover accepted topic taxonomy."
    )
    taxonomy_sub = p_taxonomy.add_subparsers(dest="taxonomy_command", required=True)

    p_taxonomy_record = taxonomy_sub.add_parser(
        "record", help="Record an accepted taxonomy JSON manifest."
    )
    _add_common_corpus_arg(p_taxonomy_record)
    p_taxonomy_record.add_argument(
        "--input",
        required=True,
        help="Accepted taxonomy JSON input.",
    )
    p_taxonomy_record.set_defaults(func=cmd_taxonomy_record, typed_command="taxonomy record")

    p_taxonomy_discover = taxonomy_sub.add_parser(
        "discover", help="Discover candidate child taxonomy nodes."
    )
    _add_common_corpus_arg(p_taxonomy_discover)
    p_taxonomy_discover.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier used to collect root topic members.",
    )
    p_taxonomy_discover.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_taxonomy_discover.add_argument(
        "--steering-feedback",
        default=None,
        help="Papyrus steering feedback JSON with reviewed suppressions.",
    )
    p_taxonomy_discover.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_taxonomy_discover.set_defaults(func=cmd_taxonomy_discover, typed_command="taxonomy discover")

    p_ontology = subparsers.add_parser(
        "ontology", help="Validate and materialize accepted ontology."
    )
    ontology_sub = p_ontology.add_subparsers(dest="ontology_command", required=True)

    p_ontology_record = ontology_sub.add_parser(
        "record", help="Record an accepted ontology JSON manifest."
    )
    _add_common_corpus_arg(p_ontology_record)
    p_ontology_record.add_argument(
        "--input",
        required=True,
        help="Accepted ontology JSON input.",
    )
    p_ontology_record.set_defaults(func=cmd_ontology_record)

    p_ontology_apply = ontology_sub.add_parser(
        "apply", help="Materialize accepted taxonomy and ontology into a graph snapshot."
    )
    _add_common_corpus_arg(p_ontology_apply)
    p_ontology_apply.add_argument(
        "--taxonomy",
        required=True,
        help="Taxonomy snapshot id or latest.",
    )
    p_ontology_apply.add_argument(
        "--relationships",
        required=True,
        help="Ontology relationship snapshot id or latest.",
    )
    p_ontology_apply.add_argument(
        "--graph-snapshot",
        required=True,
        help="Graph snapshot reference in extractor_id:snapshot_id form.",
    )
    p_ontology_apply.set_defaults(func=cmd_ontology_apply)

    p_ontology_query = ontology_sub.add_parser(
        "query", help="Query accepted ontology relationship assertions."
    )
    _add_common_corpus_arg(p_ontology_query)
    p_ontology_query.add_argument(
        "--relationships",
        required=True,
        help="Ontology relationship snapshot id or latest.",
    )
    p_ontology_query.add_argument("--source-ref", default=None, help="Source reference filter.")
    p_ontology_query.add_argument(
        "--relationship",
        default=None,
        help="Relationship type filter.",
    )
    p_ontology_query.add_argument(
        "--direction",
        choices=["outbound", "inbound", "both"],
        default="outbound",
        help="Relationship direction filter.",
    )
    p_ontology_query.set_defaults(func=cmd_ontology_query)
