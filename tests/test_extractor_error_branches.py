import os
from types import SimpleNamespace

import pytest

from biblicus.extractors import (
    aws_transcribe_stt,
    azure_speech_stt,
    deepgram_stt,
    google_speech_stt,
)
from biblicus.errors import ExtractionSnapshotFatalError


def test_aws_transcribe_missing_dependency(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "y")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    import builtins
    orig_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if name == "boto3":
            raise ImportError("missing")
        return orig_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    config = {
        "s3_bucket": "b",
        "region_name": "us-west-2",
        "language_code": "en-US",
    }
    with pytest.raises(ExtractionSnapshotFatalError):
        aws_transcribe_stt.AwsTranscribeSpeechToTextExtractor().validate_config(config)


def test_azure_speech_missing_dependency(monkeypatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    with pytest.raises(ExtractionSnapshotFatalError):
        azure_speech_stt.AzureSpeechToTextExtractor().validate_config({})


def test_deepgram_stt_missing_metadata_returns_none(monkeypatch):
    extractor = deepgram_stt.DeepgramSpeechToTextExtractor()
    # force dependency ImportError path
    from importlib import import_module
    def fake_import(name, *args, **kwargs):
        if name.startswith("deepgram"):
            raise ImportError("missing")
        return import_module(name, *args, **kwargs)
    import builtins
    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setenv("DEEPGRAM_API_KEY", "key")
    config = deepgram_stt.DeepgramSpeechToTextExtractorConfig()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(
            corpus=SimpleNamespace(root="."),
            item=SimpleNamespace(media_type="audio/wav", relpath="x.wav"),
            config=config,
            previous_extractions=[SimpleNamespace(metadata={})],
        )


def test_google_speech_missing_dependency(monkeypatch):
    monkeypatch.setattr(google_speech_stt, "speech", None, raising=False)
    with pytest.raises(ExtractionSnapshotFatalError):
        google_speech_stt.GoogleSpeechToTextExtractor().validate_config({})
