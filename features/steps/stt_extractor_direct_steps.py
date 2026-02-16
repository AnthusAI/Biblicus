from __future__ import annotations

import os
import sys
import types
import tempfile
from pathlib import Path

from behave import given, when, then

from biblicus.extractors import azure_speech_stt
from biblicus.errors import ExtractionSnapshotFatalError


@given('fake azure speech sdk is available')
def step_fake_azure_sdk(context):
    class FakeSpeech:
        class SpeechConfig:
            def __init__(self, subscription=None, endpoint=None, region=None):
                self.subscription = subscription
                self.endpoint = endpoint
                self.region = region

            def set_profanity(self, *args, **kwargs):
                pass

            def enable_dictation(self):
                pass

        class ProfanityOption:
            Masked = "masked"
            Removed = "removed"
            Raw = "raw"

        class audio:
            class AudioConfig:
                def __init__(self, filename):
                    self.filename = filename

        class SpeechRecognizer:
            def __init__(self, *args, **kwargs):
                pass

            def recognize_once(self):
                class R:
                    reason = FakeSpeech.ResultReason.NoMatch
                    text = ""

                return R()

        class ResultReason:
            RecognizedSpeech = "RecognizedSpeech"
            NoMatch = "NoMatch"
            Canceled = "Canceled"

    sys.modules["azure"] = types.SimpleNamespace()
    sys.modules["azure.cognitiveservices"] = types.SimpleNamespace()
    sys.modules["azure.cognitiveservices.speech"] = FakeSpeech
    context.fake_azure_installed = True


@given('environment variable "AZURE_SPEECH_KEY" is unset')
def step_unset_azure_key(context):
    if "AZURE_SPEECH_KEY" in os.environ:
        os.environ.pop("AZURE_SPEECH_KEY")


@when('I run the azure speech extractor directly with item "{filename}"')
def step_run_azure_extractor(context, filename):
    if not hasattr(context, "tmp_dir"):
        context.tmp_dir = tempfile.mkdtemp(prefix="azure-stt-")
    audio_path = Path(context.tmp_dir) / filename
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"RIFF")
    extractor = azure_speech_stt.AzureSpeechToTextExtractor()
    context.azure_error = None
    try:
        extractor.extract_text(
            corpus=types.SimpleNamespace(root=Path(context.tmp_dir)),
            item=types.SimpleNamespace(relpath=str(audio_path.relative_to(context.tmp_dir)), media_type="audio/wav"),
            config=azure_speech_stt.AzureSpeechToTextExtractorConfig.model_validate(
                {"language": "en-US", "region": "eastus", "profanity_option": "raw"}
            ),
            previous_extractions=[],
        )
    except Exception as exc:  # noqa: BLE001
        context.azure_error = exc


@then('the extraction fails with a fatal error containing "{message}"')
def step_assert_azure_error(context, message):
    assert isinstance(context.azure_error, ExtractionSnapshotFatalError)
    text = str(context.azure_error)
    assert message in text or "optional dependency" in text
