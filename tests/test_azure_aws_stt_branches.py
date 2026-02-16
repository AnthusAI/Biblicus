import types
import sys

import pytest

from biblicus.extractors import aws_transcribe_stt, azure_speech_stt
from biblicus.errors import ExtractionSnapshotFatalError


def test_azure_missing_dependency(monkeypatch, tmp_path):
    # Simulate missing optional dependency and missing API key
    monkeypatch.setitem(sys.modules, "azure.cognitiveservices.speech", None)
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    extractor = azure_speech_stt.AzureSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.validate_config({"language": "en-US", "region": "eastus"})


def test_aws_transcribe_failure_and_timeout(monkeypatch, tmp_path):
    item = types.SimpleNamespace(
        id="i1",
        relpath="raw/a.wav",
        sha256="abc",
        bytes=1,
        media_type="audio/wav",
        title=None,
        tags=[],
        metadata={},
        source_uri=None,
    )
    corpus = types.SimpleNamespace(root=tmp_path)
    audio_path = tmp_path / item.relpath
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"RIFFxxxx")

    class FailTranscribe:
        def __init__(self):
            self.calls = 0

        def start_transcription_job(self, **kwargs):
            return None

        def get_transcription_job(self, TranscriptionJobName):
            self.calls += 1
            return {"TranscriptionJob": {"TranscriptionJobStatus": "FAILED", "FailureReason": "boom"}}

        def delete_transcription_job(self, TranscriptionJobName):
            return None

    class SlowTranscribe(FailTranscribe):
        def get_transcription_job(self, TranscriptionJobName):
            self.calls += 1
            return {"TranscriptionJob": {"TranscriptionJobStatus": "IN_PROGRESS"}}

    class FakeS3:
        def upload_fileobj(self, fh, bucket, key):
            self.uploaded = (bucket, key)

        def delete_object(self, Bucket, Key):
            return None

    # Failure path
    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=lambda name, region_name=None: FakeS3() if name == "s3" else FailTranscribe()))
    extractor = aws_transcribe_stt.AwsTranscribeSpeechToTextExtractor()
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(
            corpus=corpus,
            item=item,
            config={"s3_bucket": "bucket", "max_wait_seconds": 0.1, "poll_interval_seconds": 0.05},
            previous_extractions=[],
        )

    # Timeout path
    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=lambda name, region_name=None: FakeS3() if name == "s3" else SlowTranscribe()))
    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(
            corpus=corpus,
            item=item,
            config={"s3_bucket": "bucket", "max_wait_seconds": 0.1, "poll_interval_seconds": 0.05},
            previous_extractions=[],
        )
