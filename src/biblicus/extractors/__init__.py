"""
Text extraction plugins for Biblicus.
"""

from __future__ import annotations

from typing import Dict

from .base import TextExtractor
from .deepgram_stt import DeepgramSpeechToTextExtractor
from .docling_granite_text import DoclingGraniteExtractor
from .docling_smol_text import DoclingSmolExtractor
from .markitdown_text import MarkItDownExtractor
from .metadata_text import MetadataTextExtractor
from .openai_stt import OpenAiSpeechToTextExtractor
from .paddleocr_vl_text import PaddleOcrVlExtractor
from .pass_through_text import PassThroughTextExtractor
from .pdf_text import PortableDocumentFormatTextExtractor
from .pipeline import PipelineExtractor
from .rapidocr_text import RapidOcrExtractor
from .select_longest_text import SelectLongestTextExtractor
from .select_override import SelectOverrideExtractor
from .select_smart_override import SelectSmartOverrideExtractor
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
        DoclingSmolExtractor.extractor_id: DoclingSmolExtractor(),
        DoclingGraniteExtractor.extractor_id: DoclingGraniteExtractor(),
        PassThroughTextExtractor.extractor_id: PassThroughTextExtractor(),
        PipelineExtractor.extractor_id: PipelineExtractor(),
        PortableDocumentFormatTextExtractor.extractor_id: PortableDocumentFormatTextExtractor(),
        OpenAiSpeechToTextExtractor.extractor_id: OpenAiSpeechToTextExtractor(),
        DeepgramSpeechToTextExtractor.extractor_id: DeepgramSpeechToTextExtractor(),
        RapidOcrExtractor.extractor_id: RapidOcrExtractor(),
        PaddleOcrVlExtractor.extractor_id: PaddleOcrVlExtractor(),
        SelectTextExtractor.extractor_id: SelectTextExtractor(),
        SelectLongestTextExtractor.extractor_id: SelectLongestTextExtractor(),
        SelectSmartOverrideExtractor.extractor_id: SelectSmartOverrideExtractor(),
        SelectOverrideExtractor.extractor_id: SelectOverrideExtractor(),
        UnstructuredExtractor.extractor_id: UnstructuredExtractor(),
    }
    if extractor_id not in extractors:
        raise KeyError(f"Unknown extractor: {extractor_id!r}")
    return extractors[extractor_id]
