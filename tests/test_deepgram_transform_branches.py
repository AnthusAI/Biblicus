import pytest

from biblicus.extractors.deepgram_transform import DeepgramTranscriptTransformExtractor, _render_deepgram_text


def test_validate_config_rejects_unknown_source():
    extractor = DeepgramTranscriptTransformExtractor()
    with pytest.raises(ValueError):
        extractor.validate_config({"source": "unknown"})


def test_render_handles_empty_channels():
    payload = {"results": {"channels": []}}
    config = extractor_config()
    assert _render_deepgram_text(payload=payload, config=config) == ""


def extractor_config():
    extractor = DeepgramTranscriptTransformExtractor()
    return extractor.validate_config({"source": "transcript"})
