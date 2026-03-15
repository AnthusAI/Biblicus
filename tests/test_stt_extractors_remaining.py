import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from biblicus.errors import ExtractionSnapshotFatalError
from biblicus.extractors import (
    aldea_stt,
    deepgram_stt,
    aws_transcribe_stt,
    azure_speech_stt,
    openai_audio_stt,
)


def test_deepgram_empty_channels_returns_empty_text(monkeypatch, tmp_path):
    audio_path = tmp_path / "a.wav"
    audio_path.write_bytes(b"RIFFdata")

    class FakeClient:
        def __init__(self):
            self.listen = SimpleNamespace(v1=SimpleNamespace(media=SimpleNamespace(transcribe_file=self._call)))

        def _call(self, request, **kwargs):  # noqa: ARG002
            return SimpleNamespace(results=SimpleNamespace(channels=[]))

    monkeypatch.setenv("DEEPGRAM_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "deepgram", SimpleNamespace(DeepgramClient=lambda api_key: FakeClient()))

    extractor = deepgram_stt.DeepgramSpeechToTextExtractor()
    config = extractor.validate_config({"model": "m"})
    item = SimpleNamespace(id="i", media_type="audio/wav", relpath=audio_path.name)
    corpus = SimpleNamespace(root=tmp_path)
    result = extractor.extract_text(corpus=corpus, item=item, config=config, previous_extractions=[])
    assert result.text == ""


def test_azure_missing_key_raises(monkeypatch):
    fake_speech_module = SimpleNamespace(
        AudioConfig=lambda filename=None: None,  # noqa: ARG002
        SpeechConfig=lambda **kwargs: None,
        SpeechRecognizer=lambda *a, **k: None,
    )
    monkeypatch.setitem(sys.modules, "azure.cognitiveservices.speech", fake_speech_module)
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)

    extractor = azure_speech_stt.AzureSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.validate_config({"region": "test"})


def test_aws_missing_creds(monkeypatch):
    # Simulate missing boto3 dependency to exercise fatal path
    real_import = __import__

    def fake_import(name, *a, **k):  # noqa: ARG002
        if name == "boto3":
            raise ImportError("no boto3")
        return real_import(name, *a, **k)

    monkeypatch.setattr("builtins.__import__", fake_import)

    extractor = aws_transcribe_stt.AwsTranscribeSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(
            corpus=SimpleNamespace(root=Path("/")),
            item=SimpleNamespace(media_type="audio/wav", relpath="a.wav", id="id1"),
            config=extractor.validate_config({"s3_bucket": "b"}),
            previous_extractions=[],
        )


def test_openai_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace())
    extractor = openai_audio_stt.OpenAiAudioSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.validate_config({"model": "whisper"})


def test_aldea_import_error(monkeypatch, tmp_path):
    monkeypatch.setenv("ALDEA_API_KEY", "key")
    audio_path = tmp_path / "a.wav"
    audio_path.write_bytes(b"data")

    real_import = __import__

    def fake_import(name, *args, **kwargs):  # noqa: ARG002
        if name == "httpx":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    extractor = aldea_stt.AldeaSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(
            corpus=SimpleNamespace(root=tmp_path),
            item=SimpleNamespace(media_type="audio/wav", relpath=audio_path.name, id="1"),
            config=extractor.validate_config({"language": "en", "diarization": True, "timestamps": True}),
            previous_extractions=[],
        )


def test_aldea_request_headers(monkeypatch, tmp_path):
    monkeypatch.setenv("ALDEA_API_KEY", "key")
    audio_path = tmp_path / "a.wav"
    audio_path.write_bytes(b"data")

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": {"channels": [{"alternatives": [{"transcript": "hi"}]}]}}

    def fake_post(url, content, params=None, headers=None, timeout=None):  # noqa: ARG002
        captured["params"] = params
        captured["headers"] = headers
        return FakeResponse()

    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(post=fake_post))
    extractor = aldea_stt.AldeaSpeechToTextExtractor()
    result = extractor.extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=SimpleNamespace(media_type="audio/wav", relpath=audio_path.name, id="1"),
        config=extractor.validate_config({"language": "en", "diarization": True, "timestamps": True}),
        previous_extractions=[],
    )
    assert captured["params"]["language"] == "en"
    assert captured["params"]["diarization"] == "true"
    assert captured["headers"]["timestamps"] == "true"
    assert result.text == "hi"
