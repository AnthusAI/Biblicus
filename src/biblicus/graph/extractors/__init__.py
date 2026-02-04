"""
Graph extractor registry for Biblicus.
"""

from __future__ import annotations

from typing import Dict, Type

from ..base import GraphExtractor
from .cooccurrence import CooccurrenceGraphExtractor
from .simple_entities import SimpleEntityGraphExtractor


def available_graph_extractors() -> Dict[str, Type[GraphExtractor]]:
    """
    Return the registered graph extractors.

    :return: Mapping of extractor identifiers to extractor classes.
    :rtype: dict[str, Type[GraphExtractor]]
    """
    return {
        CooccurrenceGraphExtractor.extractor_id: CooccurrenceGraphExtractor,
        SimpleEntityGraphExtractor.extractor_id: SimpleEntityGraphExtractor,
    }


def get_graph_extractor(extractor_id: str) -> GraphExtractor:
    """
    Instantiate a graph extractor by identifier.

    :param extractor_id: Graph extractor identifier.
    :type extractor_id: str
    :return: Graph extractor instance.
    :rtype: GraphExtractor
    :raises KeyError: If the extractor identifier is unknown.
    """
    registry = available_graph_extractors()
    extractor_class = registry.get(extractor_id)
    if extractor_class is None:
        known = ", ".join(sorted(registry.keys())) or "none"
        raise KeyError(f"Unknown graph extractor '{extractor_id}'. Known graph extractors: {known}")
    return extractor_class()
