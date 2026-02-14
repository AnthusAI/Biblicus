from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from typing import Any, Dict, Optional

from behave import given, then


@dataclass
class _FakeAwsTranscriptionBehavior:
    transcript: str
    job_status: str = "COMPLETED"
    failure_reason: Optional[str] = None
    speaker_labels: Optional[Dict[str, Any]] = None


def _ensure_fake_aws_transcription_behaviors(
    context,
) -> Dict[str, _FakeAwsTranscriptionBehavior]:
    behaviors = getattr(context, "fake_aws_transcriptions", None)
    if behaviors is None:
        behaviors = {}
        context.fake_aws_transcriptions = behaviors
    return behaviors


def _install_fake_boto3_module(context) -> None:
    already_installed = getattr(context, "_fake_boto3_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    if "boto3" in sys.modules:
        original_modules["boto3"] = sys.modules["boto3"]
    if "botocore" in sys.modules:
        original_modules["botocore"] = sys.modules["botocore"]

    behaviors = _ensure_fake_aws_transcription_behaviors(context)

    class _FakeS3Client:
        def __init__(self, service_name: str, region_name: str) -> None:
            boto3_module.last_s3_service = service_name  # type: ignore[attr-defined]
            boto3_module.last_s3_region = region_name  # type: ignore[attr-defined]
            boto3_module.uploads = []  # type: ignore[attr-defined]
            boto3_module.deletes = []  # type: ignore[attr-defined]

        def upload_fileobj(self, fileobj: Any, bucket: str, key: str) -> None:
            boto3_module.uploads.append({"bucket": bucket, "key": key})  # type: ignore[attr-defined]
            boto3_module.last_upload_bucket = bucket  # type: ignore[attr-defined]
            boto3_module.last_upload_key = key  # type: ignore[attr-defined]

        def delete_object(self, Bucket: str, Key: str) -> None:
            boto3_module.deletes.append({"bucket": Bucket, "key": Key})  # type: ignore[attr-defined]

    class _FakeTranscribeClient:
        def __init__(self, service_name: str, region_name: str) -> None:
            boto3_module.last_transcribe_service = service_name  # type: ignore[attr-defined]
            boto3_module.last_transcribe_region = region_name  # type: ignore[attr-defined]
            boto3_module.jobs = {}  # type: ignore[attr-defined]

        def start_transcription_job(self, **kwargs: Any) -> None:
            job_name = kwargs["TranscriptionJobName"]
            media_uri = kwargs["Media"]["MediaFileUri"]
            media_format = kwargs["MediaFormat"]
            language_code = kwargs["LanguageCode"]
            settings = kwargs.get("Settings", {})

            boto3_module.last_job_name = job_name  # type: ignore[attr-defined]
            boto3_module.last_media_uri = media_uri  # type: ignore[attr-defined]
            boto3_module.last_media_format = media_format  # type: ignore[attr-defined]
            boto3_module.last_language_code = language_code  # type: ignore[attr-defined]
            boto3_module.last_settings = settings  # type: ignore[attr-defined]

            # Extract bucket and key from S3 URI
            s3_key = media_uri.replace("s3://", "").split("/", 1)[1]
            filename = s3_key.split("/")[-1]

            # Find behavior for this filename
            behavior = behaviors.get(filename)
            if behavior is None:
                behavior = _FakeAwsTranscriptionBehavior(transcript="")

            boto3_module.jobs[job_name] = {  # type: ignore[attr-defined]
                "status": behavior.job_status,
                "transcript": behavior.transcript,
                "failure_reason": behavior.failure_reason,
                "speaker_labels": behavior.speaker_labels,
                "language_code": language_code,
                "settings": settings
            }

        def get_transcription_job(self, TranscriptionJobName: str) -> Dict[str, Any]:
            job = boto3_module.jobs.get(TranscriptionJobName, {})  # type: ignore[attr-defined]
            status = job.get("status", "COMPLETED")
            response = {
                "TranscriptionJob": {
                    "TranscriptionJobStatus": status
                }
            }

            if status == "COMPLETED":
                transcript_data = {
                    "results": {
                        "transcripts": [{"transcript": job.get("transcript", "")}]
                    }
                }
                if job.get("speaker_labels"):
                    transcript_data["results"]["speaker_labels"] = job["speaker_labels"]

                # Store transcript data in module for retrieval
                boto3_module.transcript_data = transcript_data  # type: ignore[attr-defined]

                # Use a fake URI that returns the transcript data
                response["TranscriptionJob"]["Transcript"] = {
                    "TranscriptFileUri": f"http://fake-transcript-uri/{TranscriptionJobName}"
                }
            elif status == "FAILED":
                response["TranscriptionJob"]["FailureReason"] = job.get("failure_reason", "Unknown")

            return response

        def delete_transcription_job(self, TranscriptionJobName: str) -> None:
            if TranscriptionJobName in boto3_module.jobs:  # type: ignore[attr-defined]
                del boto3_module.jobs[TranscriptionJobName]  # type: ignore[attr-defined]

    # Mock boto3.client to return appropriate fake clients
    def client(service_name: str, region_name: str = "us-east-1") -> Any:
        if service_name == "s3":
            return _FakeS3Client(service_name, region_name)
        elif service_name == "transcribe":
            return _FakeTranscribeClient(service_name, region_name)
        else:
            raise ValueError(f"Unsupported service: {service_name}")

    boto3_module = types.ModuleType("boto3")
    boto3_module.client = client
    boto3_module.last_s3_service = None
    boto3_module.last_s3_region = None
    boto3_module.last_transcribe_service = None
    boto3_module.last_transcribe_region = None
    boto3_module.last_job_name = None
    boto3_module.last_media_uri = None
    boto3_module.last_media_format = None
    boto3_module.last_language_code = None
    boto3_module.last_settings = {}
    boto3_module.last_upload_bucket = None
    boto3_module.last_upload_key = None
    boto3_module.uploads = []
    boto3_module.deletes = []
    boto3_module.jobs = {}
    boto3_module.transcript_data = None

    # Mock urllib.request.urlopen to return fake transcript data
    import urllib.request as urllib_request_module
    original_urlopen = urllib_request_module.urlopen

    def fake_urlopen(url: str) -> Any:
        if "fake-transcript-uri" in str(url):
            import io
            data = json.dumps(boto3_module.transcript_data).encode('utf-8')  # type: ignore[attr-defined]

            class FakeResponse:
                def read(self) -> bytes:
                    return data

                def __enter__(self) -> Any:
                    return self

                def __exit__(self, *args: Any) -> None:
                    pass

            return FakeResponse()
        return original_urlopen(url)

    urllib_request_module.urlopen = fake_urlopen
    context._fake_urlopen_original = original_urlopen

    sys.modules["boto3"] = boto3_module
    context._fake_boto3_installed = True
    context._fake_boto3_original_modules = original_modules


def _install_boto3_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_boto3_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    if "boto3" in sys.modules:
        original_modules["boto3"] = sys.modules["boto3"]

    boto3_module = types.ModuleType("boto3")
    sys.modules["boto3"] = boto3_module

    context._fake_boto3_unavailable_installed = True
    context._fake_boto3_unavailable_original_modules = original_modules


@given("a fake boto3 library is available")
def step_fake_boto3_available(context) -> None:
    _install_fake_boto3_module(context)


@given(
    'a fake boto3 library is available that returns transcript "{transcript}" for filename "{filename}"'
)
def step_fake_boto3_returns_transcript(context, transcript: str, filename: str) -> None:
    _install_fake_boto3_module(context)
    behaviors = _ensure_fake_aws_transcription_behaviors(context)
    behaviors[filename] = _FakeAwsTranscriptionBehavior(transcript=transcript)


@given(
    'a fake boto3 library is available that returns failed job for filename "{filename}" with reason "{reason}"'
)
def step_fake_boto3_returns_failed_job(context, filename: str, reason: str) -> None:
    _install_fake_boto3_module(context)
    behaviors = _ensure_fake_aws_transcription_behaviors(context)
    behaviors[filename] = _FakeAwsTranscriptionBehavior(
        transcript="",
        job_status="FAILED",
        failure_reason=reason
    )


@given("the boto3 dependency is unavailable")
def step_boto3_dependency_unavailable(context) -> None:
    _install_boto3_unavailable_module(context)


@then('the AWS Transcribe job used language code "{language_code}"')
def step_aws_transcribe_used_language_code(context, language_code: str) -> None:
    _ = context
    boto3_module = sys.modules.get("boto3")
    assert boto3_module is not None
    actual = getattr(boto3_module, "last_language_code", None)
    assert actual == language_code


@then('the AWS Transcribe job used media format "{media_format}"')
def step_aws_transcribe_used_media_format(context, media_format: str) -> None:
    _ = context
    boto3_module = sys.modules.get("boto3")
    assert boto3_module is not None
    actual = getattr(boto3_module, "last_media_format", None)
    assert actual == media_format


@then("the AWS Transcribe job enabled speaker labels")
def step_aws_transcribe_enabled_speaker_labels(context) -> None:
    _ = context
    boto3_module = sys.modules.get("boto3")
    assert boto3_module is not None
    settings = getattr(boto3_module, "last_settings", {})
    assert settings.get("ShowSpeakerLabels") is True
