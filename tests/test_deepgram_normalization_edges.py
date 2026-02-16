import json
from datetime import datetime

from biblicus.extractors.deepgram_stt import _deepgram_response_to_dict, _normalize_deepgram_value


def test_deepgram_response_prefers_to_dict_datetime_iso():
    class Response:
        def to_dict(self):
            return {"timestamp": datetime(2020, 1, 1, 0, 0, 0)}

    result = _deepgram_response_to_dict(Response())
    assert result["timestamp"].startswith("2020-01-01T00:00:00")


def test_deepgram_response_falls_back_to_json():
    class Response:
        def to_dict(self):
            raise RuntimeError("boom")

        def to_json(self):
            return json.dumps({"nested": {"value": 3}})

    assert _deepgram_response_to_dict(Response()) == {"nested": {"value": 3}}


def test_deepgram_normalize_handles_dicts_lists_and_unserializable():
    class Inner:
        def __init__(self):
            self.payload = {"a": {"b": 1}}

    class Outer:
        def __init__(self):
            self.inner = Inner()
            self.mixed = {"set": {1, 2}}

    normalized = _normalize_deepgram_value(Outer())
    # set is coerced to string fallback while nested dict stays intact
    assert normalized["inner"]["payload"] == {"a": {"b": 1}}
    assert "set" in normalized["mixed"]
