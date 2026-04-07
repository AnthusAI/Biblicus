import sys
from types import SimpleNamespace


from biblicus.corpus import Corpus
from biblicus.graph.extractors.dependency_relations import _extract_relations
from biblicus.graph.extractors.ner_entities import _extract_entities
from biblicus.graph.extractors.simple_entities import (
    SimpleEntitiesGraphExtractor,
    SimpleEntityGraphConfig,
)
from biblicus.workflow import _list_retrieval_snapshots


def test_simple_entities_accepts_base_model_config():
    extractor = SimpleEntitiesGraphExtractor()
    config = SimpleEntityGraphConfig()
    validated = extractor.validate_config(config)
    assert isinstance(validated, SimpleEntityGraphConfig)


def test_dependency_relations_skip_short_entities(monkeypatch):
    object_token = SimpleNamespace(dep_="dobj", text="it")
    verb_token = SimpleNamespace(
        dep_="ROOT", text="likes", lemma_="like", children=[object_token]
    )
    subject_token = SimpleNamespace(dep_="nsubj", text="I", head=verb_token)

    class _FakeDoc(list):
        def __iter__(self):
            return super().__iter__()

    fake_doc = _FakeDoc([subject_token])

    monkeypatch.setattr(
        "biblicus.graph.extractors.dependency_relations._load_doc",
        lambda text, model_name: fake_doc,
    )

    relations = _extract_relations(
        extracted_text="I like it", model_name="fake", min_length=3
    )
    assert relations == []


def test_ner_entities_skip_short_entities(monkeypatch):
    fake_ent = SimpleNamespace(text="NY", label_="GPE")
    fake_doc = SimpleNamespace(ents=[fake_ent])
    class _FakeNlp:
        def __call__(self, text: str):
            return fake_doc

    fake_spacy = SimpleNamespace(load=lambda model: _FakeNlp())
    monkeypatch.setitem(sys.modules, "spacy", fake_spacy)
    entities = _extract_entities(
        extracted_text="NY", model_name="fake", min_length=3
    )
    assert entities == []


def test_list_retrieval_snapshots_ignores_bad_manifests(tmp_path, monkeypatch):
    corpus = Corpus(tmp_path)
    retriever_dir = corpus.retrieval_dir / "scan"
    snapshot_dir = retriever_dir / "snap-1"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(corpus, "load_snapshot", lambda name: (_ for _ in ()).throw(ValueError()))
    snapshots = _list_retrieval_snapshots(corpus)
    assert snapshots == []
