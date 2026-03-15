import os
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from biblicus.analysis.models import MarkovAnalysisSpanMarkupSegmentationConfig
from biblicus.analysis import topic_modeling
from biblicus.extractors import (
    aldea_stt,
    aws_transcribe_stt,
    azure_speech_stt,
    deepgram_stt,
    deepgram_transform,
    google_speech_stt,
)
from biblicus.errors import ExtractionSnapshotFatalError


def test_span_markup_overlap_requires_chunk_chars():
    with pytest.raises(ValueError):
        MarkovAnalysisSpanMarkupSegmentationConfig(
            prompt_template="tpl",
            chunk_overlap_characters=5,
        )
    with pytest.raises(ValueError):
        MarkovAnalysisSpanMarkupSegmentationConfig(
            prompt_template="tpl",
            chunk_characters=5,
            chunk_overlap_characters=6,
        )


def test_topic_modeling_log_interval_branches(monkeypatch):
    docs = [topic_modeling.TopicModelingDocument(document_id=str(i), source_item_id="", text="t") for i in range(120)]
    config = topic_modeling.TopicModelingEntityRemovalConfig(
        enabled=True,
        provider="spacy",
        model="demo",
        regex_patterns=["t"],
        regex_replace_with=" ",
    )
    fake_doc = SimpleNamespace(ents=[])
    fake_spacy = SimpleNamespace(load=lambda model: lambda text: fake_doc)
    monkeypatch.setitem(sys.modules, "spacy", fake_spacy)
    calls = {"count": 0}
    import builtins
    monkeypatch.setattr(builtins, "print", lambda *a, **k: calls.update(count=calls["count"] + 1))
    report, processed = topic_modeling._apply_entity_removal(
        documents=docs,
        config=config,
        cache_path=None,
    )
    assert report.output_documents == len(processed)
    assert calls["count"] > 0


def test_aws_transcribe_validate_requires_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "boto3", None)
    with pytest.raises(ExtractionSnapshotFatalError):
        aws_transcribe_stt.AwsTranscribeSpeechToTextExtractor().validate_config({})


def test_azure_speech_validate_requires_key(monkeypatch):
    fake_speech = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "azure", SimpleNamespace(cognitiveservices=SimpleNamespace(speech=fake_speech)))
    monkeypatch.setitem(sys.modules, "azure.cognitiveservices", SimpleNamespace(speech=fake_speech))
    monkeypatch.setitem(sys.modules, "azure.cognitiveservices.speech", fake_speech)
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    with pytest.raises(ExtractionSnapshotFatalError):
        azure_speech_stt.AzureSpeechToTextExtractor().validate_config({})


def test_aldea_stt_validate_requires_key(monkeypatch):
    monkeypatch.delenv("ALDEA_API_KEY", raising=False)
    import builtins

    orig_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "httpx":
            raise ImportError("missing")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ExtractionSnapshotFatalError):
        aldea_stt.AldeaSpeechToTextExtractor().validate_config({})


def test_google_speech_non_audio_returns_none():
    extractor = google_speech_stt.GoogleSpeechToTextExtractor()
    result = extractor.extract_text(
        corpus=SimpleNamespace(root=Path(".")),
        item=SimpleNamespace(media_type="text/plain"),
        config=google_speech_stt.GoogleSpeechToTextExtractorConfig(),
        previous_extractions=[],
    )
    assert result is None


def test_deepgram_stt_missing_payload_paths(monkeypatch):
    extractor = deepgram_stt.DeepgramSpeechToTextExtractor()
    dummy_output = SimpleNamespace(metadata={}, text="t")
    # _extract is not defined; we just call _find_audio_payload via extract_text using non-audio
    result = extractor.extract_text(
        corpus=SimpleNamespace(root=Path(".")),
        item=SimpleNamespace(media_type="text/plain"),
        config=deepgram_stt.DeepgramSpeechToTextExtractorConfig(),
        previous_extractions=[],
    )
    assert result is None


def test_deepgram_transform_handles_missing_channels():
    payload = {"results": {"channels": []}}
    cfg = deepgram_transform.DeepgramTranscriptTransformConfig()
    # should not raise and return empty string when no channels/alternatives
    assert deepgram_transform._render_deepgram_text(payload=payload, config=cfg) == ""
