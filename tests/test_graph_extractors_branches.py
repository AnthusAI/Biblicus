from biblicus.graph.extractors.dependency_relations import DependencyRelationsGraphExtractor
from biblicus.graph.extractors.ner_entities import NerEntitiesGraphExtractor
from biblicus.graph.extractors.simple_entities import SimpleEntitiesGraphExtractor
from biblicus.models import CatalogItem, GraphExtractionResult
from biblicus.corpus import Corpus


def _text_item():
    return CatalogItem(
        id="i",
        relpath="raw/a.txt",
        sha256="h",
        bytes=1,
        media_type="text/plain",
        title=None,
        tags=[],
        metadata={},
        created_at="now",
        source_uri="file://a",
    )


def test_dependency_relations_validates_config(tmp_path):
    extractor = DependencyRelationsGraphExtractor()
    item = _text_item()
    corpus = Corpus(tmp_path)
    res = extractor.extract_graph(
        corpus=corpus,
        item=item,
        extracted_text="alpha beta",
        config={"model": "en_core_web_sm", "min_entity_length": 2, "include_item_node": False},
    )
    assert isinstance(res, GraphExtractionResult)


def test_ner_entities_validates_config(tmp_path):
    extractor = NerEntitiesGraphExtractor()
    item = _text_item()
    corpus = Corpus(tmp_path)
    res = extractor.extract_graph(
        corpus=corpus,
        item=item,
        extracted_text="New York is great",
        config={"model": "en_core_web_sm", "min_entity_length": 2, "include_item_node": False},
    )
    assert isinstance(res, GraphExtractionResult)


def test_simple_entities_validates_config(tmp_path):
    extractor = SimpleEntitiesGraphExtractor()
    item = _text_item()
    corpus = Corpus(tmp_path)
    res = extractor.extract_graph(
        corpus=corpus,
        item=item,
        extracted_text="Entity one",
        config={"model": "en_core_web_sm", "min_entity_length": 2, "include_item_node": False},
    )
    assert isinstance(res, GraphExtractionResult)
