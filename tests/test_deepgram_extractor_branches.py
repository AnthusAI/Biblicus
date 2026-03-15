import types
import sys
from pathlib import Path

import pytest

from biblicus.extractors import deepgram_stt
from biblicus.errors import ExtractionSnapshotFatalError


def test_deepgram_missing_dependency(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "deepgram", None)
    extractor = deepgram_stt.DeepgramSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.validate_config({"api_key": "k"})


def test_deepgram_transcription_success(monkeypatch, tmp_path):
    audio = tmp_path / "raw"
    audio.mkdir()
    audio_file = audio / "a.wav"
    audio_file.write_bytes(b"RIFF")

    class Alt:
        transcript = "hello"

    class Channel:
        alternatives = [Alt()]

    class Results:
        channels = [Channel()]

    class Resp:
        results = Results()

    class FakeListen:
        class v1:
            class media:
                @staticmethod
                def transcribe_file(request, **kwargs):
                    return Resp()

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.listen = FakeListen()

    monkeypatch.setitem(sys.modules, "deepgram", types.SimpleNamespace(DeepgramClient=FakeClient))

    monkeypatch.setattr(deepgram_stt, "resolve_deepgram_api_key", lambda: "k")
    extractor = deepgram_stt.DeepgramSpeechToTextExtractor()
    config = deepgram_stt.DeepgramSpeechToTextExtractorConfig.model_validate(
        {
            "model": "nova",
            "punctuate": True,
            "language": "en",
            "diarize": False,
            "smart_format": True,
            "filler_words": False,
        }
    )
    result = extractor.extract_text(
        corpus=types.SimpleNamespace(root=tmp_path),
        item=types.SimpleNamespace(relpath="raw/a.wav", media_type="audio/wav"),
        config=config,
        previous_extractions=[],
    )
    assert result.text == "hello"
