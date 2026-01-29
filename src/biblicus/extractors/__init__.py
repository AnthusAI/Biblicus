"""
Text extraction plugins for Biblicus.
"""

from __future__ import annotations

from typing import Dict

from .base import TextExtractor
from .markitdown_text import MarkItDownExtractor
from .metadata_text import MetadataTextExtractor
from .openai_stt import OpenAiSpeechToTextExtractor
from .pass_through_text import PassThroughTextExtractor
from .pdf_text import PortableDocumentFormatTextExtractor
from .pipeline import PipelineExtractor
from .rapidocr_text import RapidOcrExtractor
from .select_longest_text import SelectLongestTextExtractor
from .select_text import SelectTextExtractor
from .unstructured_text import UnstructuredExtractor


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
        MetadataTextExtractor.extractor_id: MetadataTextExtractor(),
        MarkItDownExtractor.extractor_id: MarkItDownExtractor(),
        PassThroughTextExtractor.extractor_id: PassThroughTextExtractor(),
        PipelineExtractor.extractor_id: PipelineExtractor(),
        PortableDocumentFormatTextExtractor.extractor_id: PortableDocumentFormatTextExtractor(),
        OpenAiSpeechToTextExtractor.extractor_id: OpenAiSpeechToTextExtractor(),
        RapidOcrExtractor.extractor_id: RapidOcrExtractor(),
        SelectTextExtractor.extractor_id: SelectTextExtractor(),
        SelectLongestTextExtractor.extractor_id: SelectLongestTextExtractor(),
        UnstructuredExtractor.extractor_id: UnstructuredExtractor(),
    }
    if extractor_id not in extractors:
        raise KeyError(f"Unknown extractor: {extractor_id!r}")
    return extractors[extractor_id]
