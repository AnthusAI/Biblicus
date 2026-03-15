import sys
from types import SimpleNamespace

from biblicus.extractors.deepgram_stt import _deepgram_response_to_dict


class DummyFile:
    def __init__(self, path):
        self.path = path


class DummyItem:
    def __init__(self, path):
        self.raw_path = path
        self.relpath = path.name
        self.id = "id1"
        self.media_type = "audio/wav"


class DummyCorpus:
    def __init__(self, path):
        self.raw_dir = path
        self.root = path


def _fake_response_with_channels(text):
    alt = SimpleNamespace(transcript=text)
    channel = SimpleNamespace(alternatives=[alt])
    return SimpleNamespace(results=SimpleNamespace(channels=[channel]))


def test_deepgram_transcript_and_metadata(tmp_path, monkeypatch):
    audio_path = tmp_path / "clip.wav"
    audio_path.write_bytes(b"RIFFdata")

    response = _fake_response_with_channels(" hello ")

    class Client:
        def __init__(self):
            self.listen = SimpleNamespace(v1=SimpleNamespace(media=SimpleNamespace(transcribe_file=self._call)))
            self.last_request = None

        def _call(self, request, **kwargs):  # noqa: ARG002
            self.last_request = request
            return response

    # Install fake deepgram SDK
    def _client_factory(api_key):  # noqa: ARG001
        return Client()

    fake_sdk = SimpleNamespace(DeepgramClient=_client_factory)
    sys.modules["deepgram"] = fake_sdk

    extractor = __import__(
        "biblicus.extractors.deepgram_stt", fromlist=["DeepgramSpeechToTextExtractor"]
    ).DeepgramSpeechToTextExtractor()

    monkeypatch.setenv("DEEPGRAM_API_KEY", "k")
    parsed = extractor.validate_config({"model": "m", "smart_format": True})
    item = DummyItem(audio_path)
    corpus = DummyCorpus(tmp_path)
    out = extractor.extract_text(corpus=corpus, item=item, config=parsed, previous_extractions=[])
    assert out.text == "hello"
    meta = out.metadata.get("deepgram")
    assert meta


def test_deepgram_response_to_dict_model_dump():
    class Resp:
        def model_dump(self):
            return {"value": 1}

    assert _deepgram_response_to_dict(Resp()) == {"value": 1}
