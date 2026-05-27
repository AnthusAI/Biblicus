"""
Named entity recognition graph extractor for Biblicus.
"""

from __future__ import annotations

import re
from collections import Counter
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ...corpus import Corpus
from ...models import CatalogItem
from ..base import GraphExtractor
from ..models import GraphEdge, GraphExtractionResult, GraphNode, GraphSchemaModel

_SPACY_PIPELINE_CACHE: dict[str, object] = {}


class NerEntitiesGraphConfig(GraphSchemaModel):
    """
    Configuration for the NER entities graph extractor.

    :ivar model: Named entity recognition model identifier.
    :vartype model: str
    :ivar min_entity_length: Minimum length for entity labels.
    :vartype min_entity_length: int
    :ivar max_entity_length: Maximum length for entity labels.
    :vartype max_entity_length: int
    :ivar entity_labels: Optional allow-list of spaCy entity labels.
    :vartype entity_labels: list[str] or None
    :ivar include_item_node: Whether to emit an item node and mentions edges.
    :vartype include_item_node: bool
    :ivar include_relation_edges: Whether to emit sentence-level entity co-occurrence edges.
    :vartype include_relation_edges: bool
    :ivar max_relation_entities_per_sentence: Maximum unique entities per sentence used for
        co-occurrence edges.
    :vartype max_relation_entities_per_sentence: int
    :ivar min_relation_weight: Minimum co-occurrence count needed to emit a relation edge.
    :vartype min_relation_weight: int
    """

    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    min_entity_length: int = Field(default=3, ge=1)
    max_entity_length: int = Field(default=120, ge=1)
    entity_labels: Optional[List[str]] = Field(default=None)
    include_item_node: bool = Field(default=True)
    include_relation_edges: bool = Field(default=False)
    max_relation_entities_per_sentence: int = Field(default=12, ge=2)
    min_relation_weight: int = Field(default=1, ge=1)


class NerEntitiesGraphExtractor(GraphExtractor):
    """
    Graph extractor that emits named entity nodes and mentions edges.
    """

    extractor_id = "ner-entities"

    def validate_config(self, config: Dict[str, object]) -> BaseModel:
        """
        Validate configuration for NER entity extraction.

        :param config: Raw configuration mapping.
        :type config: dict[str, object]
        :return: Parsed configuration.
        :rtype: NerEntitiesGraphConfig
        """
        return NerEntitiesGraphConfig.model_validate(config)

    def extract_graph(
        self,
        *,
        corpus: Corpus,
        item: CatalogItem,
        extracted_text: str,
        config: BaseModel,
    ) -> GraphExtractionResult:
        """
        Extract graph nodes and edges for a single item.

        :param corpus: Corpus containing the item.
        :type corpus: Corpus
        :param item: Catalog item to extract from.
        :type item: CatalogItem
        :param extracted_text: Text to analyze.
        :type extracted_text: str
        :param config: Parsed configuration model.
        :type config: BaseModel
        :return: Graph extraction results.
        :rtype: GraphExtractionResult
        """
        _ = corpus
        parsed = config if isinstance(config, NerEntitiesGraphConfig) else None
        if parsed is None:
            parsed = NerEntitiesGraphConfig.model_validate(config)

        entities = _extract_entities(
            extracted_text=extracted_text,
            model_name=parsed.model,
            min_length=parsed.min_entity_length,
            max_length=parsed.max_entity_length,
            entity_labels=parsed.entity_labels,
        )
        entity_counts = Counter(entity for entity, _label, _sentence_index in entities)
        entity_types = {entity: label for entity, label, _sentence_index in entities}

        nodes = _build_entity_nodes(entity_counts, entity_types)
        edges: List[GraphEdge] = []

        if parsed.include_item_node:
            item_node = GraphNode(
                node_id=f"item:{item.id}",
                node_type="item",
                label=item.title or item.relpath,
                properties={"item_id": item.id},
            )
            nodes.insert(0, item_node)
            edges.extend(_build_mentions_edges(item_node.node_id, entity_counts))

        if parsed.include_relation_edges:
            edges.extend(
                _build_relation_edges(
                    entities,
                    max_entities_per_sentence=parsed.max_relation_entities_per_sentence,
                    min_relation_weight=parsed.min_relation_weight,
                )
            )

        return GraphExtractionResult(item_id=item.id, nodes=nodes, edges=edges)


def _extract_entities(
    *,
    extracted_text: str,
    model_name: str,
    min_length: int,
    max_length: int,
    entity_labels: Optional[List[str]],
) -> List[Tuple[str, str, int]]:
    nlp = _load_spacy_pipeline(model_name)
    doc = nlp(extracted_text)
    entities: List[Tuple[str, str, int]] = []
    allowed_labels = set(entity_labels or []) or None
    for ent in getattr(doc, "ents", []):
        label = getattr(ent, "label_", "ENTITY")
        if allowed_labels is not None and label not in allowed_labels:
            continue
        text = ent.text.strip()
        if len(text) < min_length or len(text) > max_length:
            continue
        if not _looks_like_entity_label(text):
            continue
        entities.append((text, label, _entity_sentence_index(ent)))
    return entities


def _load_spacy_pipeline(model_name: str):
    cached = _SPACY_PIPELINE_CACHE.get(model_name)
    if cached is not None:
        return cached
    try:
        import spacy
    except ImportError as exc:
        raise ValueError(
            "NER graph extraction requires spaCy. Install it with pip install spacy."
        ) from exc
    pipeline = spacy.load(model_name)
    _SPACY_PIPELINE_CACHE[model_name] = pipeline
    return pipeline


def _entity_sentence_index(entity) -> int:
    try:
        sent = entity.sent
        return int(getattr(sent, "start", 0))
    except Exception:
        return 0


def _looks_like_entity_label(text: str) -> bool:
    if re.search(r"[\r\n\t]", text):
        return False
    if re.search(r",\d|\d[A-Z]", text):
        return False
    if re.match(r"^[A-Z]\.\s+[A-Z]", text):
        return False
    if not re.search(r"[A-Za-z]", text):
        return False
    return re.match(r"^[A-Z][A-Za-z0-9&.,'’/()\- ]*$", text) is not None


def _canonicalize(label: str) -> str:
    lowered = label.lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", lowered)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or lowered


def _build_entity_nodes(
    entity_counts: Counter[str], entity_types: Dict[str, str]
) -> List[GraphNode]:
    nodes: List[GraphNode] = []
    for label in sorted(entity_counts.keys()):
        canonical = _canonicalize(label)
        nodes.append(
            GraphNode(
                node_id=f"entity:{canonical}",
                node_type="entity",
                label=label,
                properties={
                    "canonical": canonical,
                    "entity_type": entity_types.get(label, "ENTITY"),
                },
            )
        )
    return nodes


def _build_mentions_edges(item_node_id: str, entity_counts: Counter[str]) -> List[GraphEdge]:
    edges: List[GraphEdge] = []
    for label, count in sorted(entity_counts.items()):
        canonical = _canonicalize(label)
        entity_id = f"entity:{canonical}"
        edge_id = f"{item_node_id}|mentions|{entity_id}"
        edges.append(
            GraphEdge(
                edge_id=edge_id,
                src=item_node_id,
                dst=entity_id,
                edge_type="mentions",
                weight=float(count),
                properties={},
            )
        )
    return edges


def _build_relation_edges(
    entities: List[Tuple[str, str, int]],
    *,
    max_entities_per_sentence: int,
    min_relation_weight: int,
) -> List[GraphEdge]:
    sentence_entities: Dict[int, List[str]] = {}
    for label, _entity_type, sentence_index in entities:
        sentence_entities.setdefault(sentence_index, []).append(_canonicalize(label))

    counts: Counter[tuple[str, str]] = Counter()
    for canonical_entities in sentence_entities.values():
        unique_entities = sorted(set(canonical_entities))[:max_entities_per_sentence]
        for left, right in combinations(unique_entities, 2):
            counts[(left, right)] += 1

    edges: List[GraphEdge] = []
    for (left, right), count in sorted(counts.items()):
        if count < min_relation_weight:
            continue
        src = f"entity:{left}"
        dst = f"entity:{right}"
        edge_id = f"{src}|related_to|{dst}"
        edges.append(
            GraphEdge(
                edge_id=edge_id,
                src=src,
                dst=dst,
                edge_type="related_to",
                weight=float(count),
                properties={"source": "sentence_cooccurrence"},
            )
        )
    return edges
