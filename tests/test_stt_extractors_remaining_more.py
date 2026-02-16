import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from biblicus.errors import ExtractionSnapshotFatalError
from biblicus.extractors import aws_transcribe_stt, azure_speech_stt, deepgram_stt, deepgram_transform, google_speech_stt


def test_aws_missing_region(monkeypatch):
    monkeypatch.setattr(aws_transcribe_stt, "boto3", SimpleNamespace(client=lambda *a, **k: None))
    extractor = aws_transcribe_stt.AwsTranscribeSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.validate_config({"s3_bucket": "b"})


def test_azure_missing_region(monkeypatch):
    speech_module = SimpleNamespace(
        AudioConfig=lambda filename=None: None,
        SpeechConfig=lambda **kwargs: None,
        SpeechRecognizer=lambda *a, **k: None,
    )
    monkeypatch.setitem(sys.modules, "azure.cognitiveservices.speech", speech_module)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "k")
    extractor = azure_speech_stt.AzureSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.validate_config({"region": None})


def test_deepgram_no_key(monkeypatch, tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"data")
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    extractor = deepgram_stt.DeepgramSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(
            corpus=SimpleNamespace(root=tmp_path),
            item=SimpleNamespace(id="i", media_type="audio/wav", relpath="a.wav"),
            config=extractor.validate_config({"model": "m"}),
            previous_extractions=[],
        )


def test_deepgram_transform_missing_dependency(monkeypatch, tmp_path):
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"data")
    real_import = __import__

    def fake_import(name, *a, **k):
        if name == "ffmpeg":
            raise ImportError("no ffmpeg")
        return real_import(name, *a, **k)

    monkeypatch.setattr("builtins.__import__", fake_import)
    extractor = deepgram_transform.DeepgramTransformExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(
            corpus=SimpleNamespace(root=tmp_path),
            item=SimpleNamespace(id="i", media_type="audio/wav", relpath="a.wav"),
            config=extractor.validate_config({}),
            previous_extractions=[],
        )


def test_google_missing_key(monkeypatch, tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"data")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setitem(sys.modules, "google.cloud", SimpleNamespace(speech=None))
    extractor = google_speech_stt.GoogleSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(
            corpus=SimpleNamespace(root=tmp_path),
            item=SimpleNamespace(id="i", media_type="audio/wav", relpath="a.wav"),
            config=extractor.validate_config({}),
            previous_extractions=[],
        )
