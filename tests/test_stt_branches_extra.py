import sys
import json
from types import ModuleType, SimpleNamespace
from pathlib import Path

import pytest

from biblicus.extractors.aws_transcribe_stt import (
    AwsTranscribeSpeechToTextExtractor,
    AwsTranscribeSpeechToTextExtractorConfig,
)
from biblicus.extractors.google_speech_stt import (
    GoogleSpeechToTextExtractor,
    GoogleSpeechToTextExtractorConfig,
)
from biblicus.models import CatalogItem
from biblicus.corpus import Corpus
from biblicus.errors import ExtractionSnapshotFatalError


def _fake_corpus_with_file(tmp_path: Path, filename: str, media_type: str) -> CatalogItem:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    relpath = Path("raw") / filename
    (tmp_path / relpath).write_bytes(b"bytes")
    return CatalogItem(
        id="item1",
        relpath=str(relpath),
        sha256="",
        bytes=5,
        media_type=media_type,
        title=None,
        tags=[],
        metadata={},
        created_at="now",
        source_uri="file://item",
    )


def test_aws_transcribe_builds_optional_settings_and_cleans_up(monkeypatch, tmp_path):
    # Fake boto3 clients to capture args and ensure cleanup paths execute.
    class FakeTranscribe:
        def __init__(self):
            self.started = None
            self.deleted = False

        def start_transcription_job(self, **kwargs):
            self.started = kwargs

        def get_transcription_job(self, TranscriptionJobName):
            return {"TranscriptionJob": {"TranscriptionJobStatus": "FAILED", "FailureReason": "boom"}}

        def delete_transcription_job(self, TranscriptionJobName):
            self.deleted = True

    class FakeS3:
        def __init__(self):
            self.deleted = False

        def upload_fileobj(self, fileobj, bucket, key):
            self.put = {"Bucket": bucket, "Key": key, "Body": fileobj.read()}

        def put_object(self, Bucket, Key, Body):
            self.put = {"Bucket": Bucket, "Key": Key, "Body": Body}

        def delete_object(self, Bucket, Key):
            self.deleted = True

    fake_transcribe = FakeTranscribe()
    fake_s3 = FakeS3()

    class FakeBoto3(ModuleType):
        def client(self, name, region_name=None):
            if name == "transcribe":
                return fake_transcribe
            if name == "s3":
                return fake_s3
            raise ValueError(name)

    sys.modules["boto3"] = FakeBoto3("boto3")

    extractor = AwsTranscribeSpeechToTextExtractor()
    config = AwsTranscribeSpeechToTextExtractorConfig(
        language_code="en-US",
        region_name="us-east-1",
        s3_bucket="bucket",
        identify_speakers=True,
        max_speakers=3,
        vocabulary_name="vocab",
        show_alternatives=True,
        max_alternatives=2,
    )
    item = _fake_corpus_with_file(tmp_path, "clip.wav", "audio/wav")
    corpus = Corpus(tmp_path)

    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(corpus=corpus, item=item, config=config, previous_extractions=[])

    assert fake_transcribe.started is not None
    settings = fake_transcribe.started["Settings"]
    assert settings["ShowSpeakerLabels"] and settings["MaxSpeakerLabels"] == 3
    assert settings["VocabularyName"] == "vocab"
    assert settings["ShowAlternatives"] and settings["MaxAlternatives"] == 2
    assert fake_transcribe.deleted is True
    assert fake_s3.deleted is True


def test_google_speech_diarization_and_confidence(monkeypatch, tmp_path):
    class FakeAlternative:
        def __init__(self, transcript, confidence=0.9):
            self.transcript = transcript
            self.confidence = confidence

    class FakeResult:
        def __init__(self, alternatives):
            self.alternatives = alternatives

    class FakeResponse:
        def __init__(self):
            self.results = [FakeResult([FakeAlternative("hello world", 0.8)])]

    class FakeRecognitionAudio:
        def __init__(self, content):
            self.content = content

    class FakeSpeakerDiarizationConfig:
        def __init__(self, enable_speaker_diarization):
            self.enable_speaker_diarization = enable_speaker_diarization
            self.min_speaker_count = None
            self.max_speaker_count = None

    class FakeRecognitionConfig:
        class AudioEncoding:
            FLAC = "flac"
            LINEAR16 = "linear16"
            OGG_OPUS = "ogg"
            ENCODING_UNSPECIFIED = None

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.enable_word_time_offsets = False
            self.diarization_config = None

    class FakeSpeechClient:
        def recognize(self, config, audio):
            self.config = config
            self.audio = audio
            return FakeResponse()

    class FakeSpeech(ModuleType):
        def __init__(self):
            super().__init__("google.cloud.speech")
            self.SpeechClient = FakeSpeechClient
            self.RecognitionConfig = FakeRecognitionConfig
            self.RecognitionAudio = FakeRecognitionAudio
            self.SpeakerDiarizationConfig = FakeSpeakerDiarizationConfig

    fake_speech = FakeSpeech()
    google_module = ModuleType("google")
    cloud_module = ModuleType("google.cloud")
    cloud_module.speech = fake_speech
    google_module.cloud = cloud_module
    sys.modules["google"] = google_module
    sys.modules["google.cloud"] = cloud_module
    sys.modules["google.cloud.speech"] = fake_speech

    extractor = GoogleSpeechToTextExtractor()
    config = GoogleSpeechToTextExtractorConfig(
        enable_word_time_offsets=True,
        enable_speaker_diarization=True,
        diarization_speaker_count=2,
    )
    item = _fake_corpus_with_file(tmp_path, "clip.flac", "audio/flac")
    corpus = Corpus(tmp_path)

    result = extractor.extract_text(corpus=corpus, item=item, config=config, previous_extractions=[])
    assert result is not None
    assert "hello world" in result.text
    assert result.metadata["confidences"][0] == 0.8


def test_aws_transcribe_success_fetches_transcript(monkeypatch, tmp_path):
    transcript_payload = {
        "results": {"transcripts": [{"transcript": "hello there"}], "speaker_labels": {}}
    }

    class FakeURLResponse:
        def __init__(self, payload):
            self.payload = payload

        def read(self):
            return json.dumps(self.payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url: FakeURLResponse(transcript_payload),
    )

    class FakeTranscribe:
        def __init__(self):
            self.started = False
            self.deleted = False

        def start_transcription_job(self, **kwargs):
            self.started = True

        def get_transcription_job(self, TranscriptionJobName):
            return {
                "TranscriptionJob": {
                    "TranscriptionJobStatus": "COMPLETED",
                    "Transcript": {"TranscriptFileUri": "http://example.com"},
                }
            }

        def delete_transcription_job(self, TranscriptionJobName):
            self.deleted = True

    class FakeS3:
        def __init__(self):
            self.deleted = False

        def upload_fileobj(self, fileobj, bucket, key):
            self.uploaded = True

        def delete_object(self, Bucket, Key):
            self.deleted = True

    fake_transcribe = FakeTranscribe()
    fake_s3 = FakeS3()

    class FakeBoto3(ModuleType):
        def client(self, name, region_name=None):
            if name == "transcribe":
                return fake_transcribe
            if name == "s3":
                return fake_s3
            raise ValueError(name)

    sys.modules["boto3"] = FakeBoto3("boto3")
    monkeypatch.setattr("time.sleep", lambda s: None)

    extractor = AwsTranscribeSpeechToTextExtractor()
    config = AwsTranscribeSpeechToTextExtractorConfig(
        language_code="en-US",
        region_name="us-east-1",
        s3_bucket="bucket",
        identify_speakers=False,
        show_alternatives=True,
        max_alternatives=2,
    )
    item = _fake_corpus_with_file(tmp_path, "clip.wav", "audio/wav")
    corpus = Corpus(tmp_path)

    result = extractor.extract_text(corpus=corpus, item=item, config=config, previous_extractions=[])
    assert result is not None
    assert "hello there" in result.text
    assert fake_transcribe.deleted and fake_s3.deleted


def test_aws_transcribe_failure_raises_and_cleans_up(monkeypatch, tmp_path):
    class FakeTranscribe:
        def __init__(self):
            self.deleted = False

        def start_transcription_job(self, **kwargs):
            return None

        def get_transcription_job(self, TranscriptionJobName):
            return {
                "TranscriptionJob": {
                    "TranscriptionJobStatus": "FAILED",
                    "FailureReason": "bad",
                    "Transcript": {"TranscriptFileUri": "http://example.com"},
                }
            }

        def delete_transcription_job(self, TranscriptionJobName):
            self.deleted = True
            raise RuntimeError("delete failed")

    class FakeS3:
        def __init__(self):
            self.deleted = False

        def upload_fileobj(self, fileobj, bucket, key):
            return None

        def delete_object(self, Bucket, Key):
            self.deleted = True
            raise RuntimeError("delete failed")

    fake_transcribe = FakeTranscribe()
    fake_s3 = FakeS3()

    class FakeBoto3(ModuleType):
        def client(self, name, region_name=None):
            if name == "transcribe":
                return fake_transcribe
            if name == "s3":
                return fake_s3
            raise ValueError(name)

    sys.modules["boto3"] = FakeBoto3("boto3")
    monkeypatch.setattr("time.sleep", lambda s: None)

    extractor = AwsTranscribeSpeechToTextExtractor()
    config = AwsTranscribeSpeechToTextExtractorConfig(
        language_code="en-US",
        region_name="us-east-1",
        s3_bucket="bucket",
    )
    item = _fake_corpus_with_file(tmp_path, "clip.wav", "audio/wav")
    corpus = Corpus(tmp_path)

    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(corpus=corpus, item=item, config=config, previous_extractions=[])
    assert fake_transcribe.deleted and fake_s3.deleted


def test_aws_transcribe_failed_status_covers_cleanup(monkeypatch, tmp_path):
    class FakeTranscribe:
        def __init__(self):
            self.deleted = False

        def start_transcription_job(self, **kwargs):
            return None

        def get_transcription_job(self, TranscriptionJobName):
            return {
                "TranscriptionJob": {
                    "TranscriptionJobStatus": "FAILED",
                    "FailureReason": "boom",
                    "Transcript": {"TranscriptFileUri": "http://example.com"},
                }
            }

        def delete_transcription_job(self, TranscriptionJobName):
            self.deleted = True

    class FakeS3:
        def __init__(self):
            self.deleted = False

        def upload_fileobj(self, fileobj, bucket, key):
            return None

        def delete_object(self, Bucket, Key):
            self.deleted = True

    fake_transcribe = FakeTranscribe()
    fake_s3 = FakeS3()

    class FakeBoto3(ModuleType):
        def client(self, name, region_name=None):
            if name == "transcribe":
                return fake_transcribe
            if name == "s3":
                return fake_s3
            raise ValueError(name)

    sys.modules["boto3"] = FakeBoto3("boto3")
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("urllib.request.urlopen", lambda url: SimpleNamespace(read=lambda: b"{}"))

    extractor = AwsTranscribeSpeechToTextExtractor()
    config = AwsTranscribeSpeechToTextExtractorConfig(
        language_code="en-US",
        region_name="us-east-1",
        s3_bucket="bucket",
        identify_speakers=True,
        max_speakers=2,
        vocabulary_name="vocab",
        show_alternatives=True,
        max_alternatives=2,
    )
    item = _fake_corpus_with_file(tmp_path, "clip.wav", "audio/wav")
    corpus = Corpus(tmp_path)

    with pytest.raises(ExtractionSnapshotFatalError):
        extractor.extract_text(corpus=corpus, item=item, config=config, previous_extractions=[])
    assert fake_transcribe.deleted and fake_s3.deleted
