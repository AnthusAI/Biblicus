"""
Deepgram-backed speech to text extractor plugin.

This extractor is implemented as an optional dependency so the core installation stays small.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..corpus import Corpus
from ..errors import ExtractionRunFatalError
from ..models import CatalogItem, ExtractedText, ExtractionStepOutput
from ..user_config import resolve_deepgram_api_key
from .base import TextExtractor


class DeepgramSpeechToTextExtractorConfig(BaseModel):
    """
    Configuration for Deepgram speech to text extraction.

    :ivar model: Deepgram transcription model identifier.
    :vartype model: str
    :ivar language: Optional language code hint for transcription.
    :vartype language: str or None
    :ivar punctuate: Whether to add punctuation to the transcript.
    :vartype punctuate: bool
    :ivar smart_format: Whether to apply smart formatting.
    :vartype smart_format: bool
    :ivar diarize: Whether to enable speaker diarization.
    :vartype diarize: bool
    :ivar filler_words: Whether to include filler words.
    :vartype filler_words: bool
    """

    model_config = ConfigDict(extra="forbid")

    model: str = Field(default="nova-3", min_length=1)
    language: Optional[str] = Field(default=None, min_length=1)
    punctuate: bool = Field(default=True)
    smart_format: bool = Field(default=True)
    diarize: bool = Field(default=False)
    filler_words: bool = Field(default=False)


class DeepgramSpeechToTextExtractor(TextExtractor):
    """
    Extractor plugin that transcribes audio items using the Deepgram API.

    This extractor is intended as a practical, hosted speech to text implementation.
    It skips non-audio items.

    :ivar extractor_id: Extractor identifier.
    :vartype extractor_id: str
    """

    extractor_id = "stt-deepgram"

    def validate_config(self, config: Dict[str, Any]) -> BaseModel:
        """
        Validate extractor configuration and ensure prerequisites are available.

        :param config: Configuration mapping.
        :type config: dict[str, Any]
        :return: Parsed configuration model.
        :rtype: DeepgramSpeechToTextExtractorConfig
        :raises ExtractionRunFatalError: If the optional dependency or required environment is missing.
        """
        try:
            from deepgram import DeepgramClient  # noqa: F401
        except ImportError as import_error:
            raise ExtractionRunFatalError(
                "Deepgram speech to text extractor requires an optional dependency. "
                'Install it with pip install "biblicus[deepgram]".'
            ) from import_error

        api_key = resolve_deepgram_api_key()
        if api_key is None:
            raise ExtractionRunFatalError(
                "Deepgram speech to text extractor requires a Deepgram API key. "
                "Set DEEPGRAM_API_KEY or configure it in ~/.biblicus/config.yml or ./.biblicus/config.yml under "
                "deepgram.api_key."
            )

        return DeepgramSpeechToTextExtractorConfig.model_validate(config)

    def extract_text(
        self,
        *,
        corpus: Corpus,
        item: CatalogItem,
        config: BaseModel,
        previous_extractions: List[ExtractionStepOutput],
    ) -> Optional[ExtractedText]:
        """
        Transcribe an audio item.

        :param corpus: Corpus containing the item bytes.
        :type corpus: Corpus
        :param item: Catalog item being processed.
        :type item: CatalogItem
        :param config: Parsed configuration model.
        :type config: DeepgramSpeechToTextExtractorConfig
        :param previous_extractions: Prior step outputs for this item within the pipeline.
        :type previous_extractions: list[biblicus.models.ExtractionStepOutput]
        :return: Extracted text payload, or None when the item is not audio.
        :rtype: ExtractedText or None
        :raises ExtractionRunFatalError: If the optional dependency or required configuration is missing.
        """
        _ = previous_extractions
        if not item.media_type.startswith("audio/"):
            return None

        parsed_config = (
            config
            if isinstance(config, DeepgramSpeechToTextExtractorConfig)
            else DeepgramSpeechToTextExtractorConfig.model_validate(config)
        )

        api_key = resolve_deepgram_api_key()
        if api_key is None:
            raise ExtractionRunFatalError(
                "Deepgram speech to text extractor requires a Deepgram API key. "
                "Set DEEPGRAM_API_KEY or configure it in ~/.biblicus/config.yml or ./.biblicus/config.yml under "
                "deepgram.api_key."
            )

        try:
            from deepgram import DeepgramClient
        except ImportError as import_error:
            raise ExtractionRunFatalError(
                "Deepgram speech to text extractor requires an optional dependency. "
                'Install it with pip install "biblicus[deepgram]".'
            ) from import_error

        client = DeepgramClient(api_key=api_key)
        source_path = corpus.root / item.relpath

        options: Dict[str, Any] = {
            "model": parsed_config.model,
            "punctuate": parsed_config.punctuate,
            "smart_format": parsed_config.smart_format,
            "diarize": parsed_config.diarize,
            "filler_words": parsed_config.filler_words,
        }
        if parsed_config.language is not None:
            options["language"] = parsed_config.language

        with source_path.open("rb") as audio_handle:
            audio_data = audio_handle.read()
            response = client.listen.rest.v("1").transcribe_file(
                {"buffer": audio_data},
                options,
            )

        transcript_text = ""
        if hasattr(response, "results") and response.results:
            channels = response.results.channels
            if channels and len(channels) > 0:
                alternatives = channels[0].alternatives
                if alternatives and len(alternatives) > 0:
                    transcript_text = alternatives[0].transcript or ""

        return ExtractedText(text=transcript_text.strip(), producer_extractor_id=self.extractor_id)
