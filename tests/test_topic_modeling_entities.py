from types import SimpleNamespace

from biblicus.analysis.topic_modeling import _remove_entities_from_text


def test_remove_entities_skips_invalid_spans():
    text = "hello world"
    bad_entity = SimpleNamespace(label_="PERSON", start_char=5, end_char=5)
    result = _remove_entities_from_text(
        text=text,
        entities=[bad_entity],
        entity_types={"PERSON"},
        replace_with="[REMOVED]",
    )
    assert result == text
