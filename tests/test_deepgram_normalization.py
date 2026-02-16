import types

from biblicus.extractors import deepgram_stt


def test_deepgram_response_to_dict_paths():
    class HasToDict:
        def to_dict(self):
            return {"a": 1}

    class HasToJson:
        def to_json(self):
            return '{"b":2}'

    class HasModelDump:
        def model_dump(self):
            return {"c": 3}

    class HasDict:
        def dict(self):
            return {"d": 4}

    assert deepgram_stt._deepgram_response_to_dict(HasToDict())["a"] == 1
    assert deepgram_stt._deepgram_response_to_dict(HasToJson())["b"] == 2
    assert deepgram_stt._deepgram_response_to_dict(HasModelDump())["c"] == 3
    assert deepgram_stt._deepgram_response_to_dict(HasDict())["d"] == 4
    assert deepgram_stt._deepgram_response_to_dict(types.SimpleNamespace(e=5)) == {"e": 5}


def test_normalize_deepgram_value_complex():
    nested = {"ts": deepgram_stt.datetime(2020, 1, 1), "list": [types.SimpleNamespace(x=1)]}
    result = deepgram_stt._normalize_deepgram_value(nested)
    assert "ts" in result and "list" in result
