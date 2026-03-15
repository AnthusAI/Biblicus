from types import SimpleNamespace

from biblicus.extractors.deepgram_transform import (
    DeepgramTranscriptTransformExtractor,
    DeepgramTranscriptTransformConfig,
    _render_deepgram_text,
)
from biblicus.models import CatalogItem, ExtractionStageOutput
from biblicus.corpus import Corpus


def _audio_item():
    return CatalogItem(
        id="i",
        relpath="raw/a.wav",
        sha256="h",
        bytes=1,
        media_type="audio/wav",
        title=None,
        tags=[],
        metadata={},
        created_at="now",
        source_uri="file://a",
    )


def test_deepgram_transform_transcript_with_labels(tmp_path):
    payload = {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {"transcript": "hello world"},
                    ]
                }
            ]
        }
    }
    config = DeepgramTranscriptTransformConfig(
        source="transcript", include_channel_labels=True, include_speaker_labels=False
    )
    text = _render_deepgram_text(payload=payload, config=config)
    assert "channel" in text.lower()


def test_deepgram_transform_utterances_filters_and_joins(tmp_path):
    payload = {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "utterances": [
                                {"channel": 0, "speaker": 1, "transcript": "one"},
                                {"channel": 1, "speaker": 2, "transcript": "two"},
                            ]
                        }
                    ]
                }
            ]
        }
    }
    config = DeepgramTranscriptTransformConfig(
        source="utterances", channels=[0], speakers=[1], include_channel_labels=True, include_speaker_labels=True
    )
    text = _render_deepgram_text(payload=payload, config=config)
    assert "one" in text
    assert "two" not in text


def test_deepgram_transform_words_includes_channel(tmp_path):
    payload = {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "words": [
                                {"channel": 0, "speaker": 1, "punctuated_word": "Hi"},
                                {"channel": 0, "speaker": 1, "punctuated_word": "there"},
                            ]
                        }
                    ]
                }
            ]
        }
    }
    config = DeepgramTranscriptTransformConfig(
        source="words", include_channel_labels=True, include_speaker_labels=True
    )
    text = _render_deepgram_text(payload=payload, config=config)
    assert "Hi" in text
    assert "channel" in text.lower()
