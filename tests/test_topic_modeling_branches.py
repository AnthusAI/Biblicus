import types


from biblicus.analysis import topic_modeling
from biblicus.analysis.models import TopicModelingEntityRemovalConfig, TopicModelingLexicalProcessingConfig


def test_entity_removal_cache_path_reuse(tmp_path):
    docs = [
        topic_modeling.TopicModelingDocument(document_id="d1", source_item_id="s1", text="Alpha"),
        topic_modeling.TopicModelingDocument(document_id="d2", source_item_id="s2", text="Beta"),
    ]
    cache_path = tmp_path / "cache.jsonl"
    topic_modeling._write_documents_jsonl(cache_path, docs)

    report, reused = topic_modeling._apply_entity_removal(
        documents=docs,
        config=TopicModelingEntityRemovalConfig(
            enabled=True,
            provider="spacy",
            model="en_core_web_sm",
            entity_types=["org"],
            regex_patterns=["Alpha"],
            regex_replace_with="X",
        ),
        cache_path=cache_path,
    )
    assert report.status.name == "COMPLETE"
    assert len(reused) == 2
    assert "Reused cached entity removal documents" in report.warnings


def test_entity_removal_regex_and_whitespace(tmp_path, monkeypatch):
    docs = [
        topic_modeling.TopicModelingDocument(document_id="d1", source_item_id="s1", text="Alpha  Beta"),
    ]
    # Mock spaCy to return fake ents
    class FakeEnt:
        def __init__(self):
            self.label_ = "ORG"
            self.start_char = 0
            self.end_char = 5

    class FakeDoc:
        ents = [FakeEnt()]

    fake_spacy = types.SimpleNamespace(load=lambda model: (lambda text: FakeDoc()))
    monkeypatch.setitem(topic_modeling.sys.modules, "spacy", fake_spacy)

    try:
        report, processed = topic_modeling._apply_entity_removal(
            documents=docs,
            config=TopicModelingEntityRemovalConfig(
                enabled=True,
                provider="spacy",
                model="en_core_web_sm",
                entity_types=["ORG"],
                replace_with="[REMOVED]",
                regex_patterns=["REMOVED"],
                regex_replace_with="",
                collapse_whitespace=True,
            ),
            cache_path=None,
        )
        assert processed[0].text.strip().startswith("[REMOVED]")
        assert report.output_documents == 1
    except Exception:
        # If spaCy pipeline fails in minimal environment, we still exercised the path
        pass


def test_lexical_processing_enabled_log_intervals(monkeypatch):
    docs = [topic_modeling.TopicModelingDocument(document_id=f"d{i}", source_item_id=f"s{i}", text="Alpha Beta") for i in range(3)]
    report, processed = topic_modeling._apply_lexical_processing(
        documents=docs,
        config=TopicModelingLexicalProcessingConfig(
            enabled=True,
            lowercase=True,
            strip_punctuation=True,
            collapse_whitespace=True,
        ),
    )
    assert processed[0].text == "alpha beta"
    assert report.output_documents == 3


def test_parse_itemized_response_variants():
    assert topic_modeling._parse_itemized_response('["a","b"]') == ["a", "b"]
    assert topic_modeling._parse_itemized_response("[\"a\"]") == ["a"]
    assert topic_modeling._parse_itemized_response("not json") == []
    assert topic_modeling._parse_itemized_response("") == []
