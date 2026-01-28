"""
Text extraction plugins for Biblicus.
"""

from __future__ import annotations

from typing import Dict

from .base import TextExtractor
from .cascade import CascadeExtractor
from .metadata_text import MetadataTextExtractor
from .pass_through_text import PassThroughTextExtractor


def get_extractor(extractor_id: str) -> TextExtractor:
    """
    Resolve a built-in text extractor by identifier.

    :param extractor_id: Extractor identifier.
    :type extractor_id: str
    :return: Extractor plugin instance.
    :rtype: TextExtractor
    :raises KeyError: If the extractor identifier is not known.
    """

    extractors: Dict[str, TextExtractor] = {
        CascadeExtractor.extractor_id: CascadeExtractor(),
        MetadataTextExtractor.extractor_id: MetadataTextExtractor(),
        PassThroughTextExtractor.extractor_id: PassThroughTextExtractor(),
    }
    if extractor_id not in extractors:
        raise KeyError(f"Unknown extractor: {extractor_id!r}")
    return extractors[extractor_id]
