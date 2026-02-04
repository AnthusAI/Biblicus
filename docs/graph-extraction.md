# Graph extraction

Graph extraction is a pipeline stage that turns extracted text into a knowledge graph. It runs after text extraction and
stores the graph in a Neo4j backend, so you can experiment with GraphRAG and graph-aware retrieval without changing
ingestion or extraction.

Graph extraction is *not* retrieval. It is a separate stage that produces a graph artifact you can query from a
graph-aware retriever or analysis tool.

## Where graph extraction sits

```
Corpus → Extraction pipeline → Extraction snapshot
                                   ↓
                        Graph extraction (pluggable)
                                   ↓
                            Neo4j (namespaced)
                                   ↓
                        Graph-aware retrievers
```

## Why use graph extraction

Use graph extraction when you need:

- Entity and relationship signals beyond lexical similarity.
- Graph traversal and community structure for retrieval expansion.
- Side-by-side comparison of extraction methods.
- A stable graph layer for GraphRAG experiments.

## Core concepts

**Graph extractor**
A pluggable component that receives extracted text for one item and returns nodes and edges.

**Graph snapshot**
A versioned record of a graph extraction run tied to a corpus and extraction snapshot.

**Graph identifier**
A deterministic identifier derived from extractor ID and configuration, used to namespace graphs in Neo4j.

## Deterministic identifiers

Graph extraction favors deterministic identifiers so runs are reproducible:

- `graph_id`: `{extractor_id}:{config_hash}`
- `node_id`: `{node_type}:{canonical_form}`
- `edge_id`: `{src}|{edge_type}|{dst}`

These IDs make it possible to deduplicate and compare graphs across extraction methods.

## Graph storage model

Graph data is stored in a single Neo4j instance. Every node and edge is namespaced with properties that identify which
corpus and graph they belong to.

Example node properties:

```
{
  "corpus_id": "research-corpus",
  "graph_id": "simple-entities:abc123",
  "extraction_snapshot_id": "pipeline:abc123",
  "item_id": "doc-42",
  "node_type": "entity",
  "node_id": "entity:person:john_smith",
  "label": "John Smith",
  "properties_json": "{\"canonical\": \"john_smith\"}"
}
```

Example edge properties:

```
{
  "corpus_id": "research-corpus",
  "graph_id": "simple-entities:abc123",
  "extraction_snapshot_id": "pipeline:abc123",
  "item_id": "doc-42",
  "edge_type": "mentions",
  "edge_id": "entity:person:john_smith|mentions|item:doc-42",
  "properties_json": "{}"
}
```

Graph properties are stored as JSON strings in the `properties_json` field so they remain stable across Neo4j versions.
If you need to query nested properties, parse the JSON in your client or load it into a structured view before querying.

## Graph extractor interface

Graph extractors follow a per-item API. They validate configuration with Pydantic and return a list of nodes and edges
for each catalog item.

Conceptual interface:

```
class GraphExtractor(ABC):
    extractor_id: str

    def validate_config(self, config: Dict[str, Any]) -> BaseModel:
        ...

    def extract_graph(
        self,
        *,
        corpus: Corpus,
        item: CatalogItem,
        extracted_text: ExtractedText,
        config: BaseModel,
    ) -> GraphExtractionResult:
        ...
```

## Running graph extraction

Graph extraction runs against an extraction snapshot. The command below builds a graph using a co-occurrence extractor
and stores it in Neo4j.

```
python -m biblicus graph extract \
  --corpus corpora/example \
  --extractor cooccurrence \
  --extraction-snapshot pipeline:RUN_ID \
  --configuration configurations/graph/cooccurrence.yml
```

If you omit `--extraction-snapshot`, Biblicus uses the latest extraction snapshot and emits a reproducibility warning.

## Example configurations

Minimal co-occurrence configuration:

```
schema_version: 1
window_size: 4
min_cooccurrence: 2
```

Minimal simple-entities configuration:

```
schema_version: 1
min_entity_length: 3
max_entity_words: 4
include_item_node: true
```

## Simple entities extractor

The `simple-entities` extractor emits entity nodes based on capitalized phrases and acronyms. It also emits:

- `mentions` edges from item nodes to entities
- `related_to` edges for entity co-occurrence within a sentence

It is deterministic and works without external dependencies, so it is a good baseline for GraphRAG experiments.

Example command:

```
python -m biblicus graph extract \
  --corpus corpora/example \
  --extractor simple-entities \
  --extraction-snapshot pipeline:RUN_ID \
  --configuration configurations/graph/simple-entities.yml
```

## Querying a logical graph

Neo4j queries are scoped by `corpus_id` and `graph_id` so you can store multiple graphs side by side:

```
MATCH (n {corpus_id: $corpus, graph_id: $graph})-[r]->(m)
WHERE n.node_type = 'entity'
RETURN n, r, m
```

## Graph-aware retrieval

Graph-aware retrievers implement the existing retriever interface. They can:

1) Extract entities from the query.
2) Match those entities to graph nodes.
3) Traverse the graph for expansion.
4) Score items by graph proximity.
5) Return evidence with graph stage scores.

This lets you combine graph signals with lexical or embedding retrievers inside a hybrid configuration.

## Local Neo4j setup

For local development, Biblicus can auto-start a local Neo4j container when graph extraction runs. The container is
started only if it is not already running. You can also run Neo4j manually via Docker:

```
python -m pip install neo4j
```

```
docker run --rm --name biblicus-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/testpassword \
  neo4j:5
```

Set Neo4j connection details in user configuration before running graph extraction.

## Repeatable integration script

Use the integration script to download a small Wikipedia corpus, run extraction, and build a Neo4j graph snapshot.
The script logs each phase so you can narrate the workflow in a demo or integration run.

```
python scripts/graph_extraction_integration.py \
  --corpus corpora/wiki_graph_demo \
  --force \
  --verify \
  --report-path reports/graph_extraction_story.md
```

## Reproducibility checklist

- Record the extraction snapshot reference used to build the graph.
- Record the graph extractor ID and configuration hash.
- Keep graph queries scoped by `corpus_id` and `graph_id`.

## Next steps

- Add additional extractors for entity and relation extraction.
- Build a graph-aware retriever and compare it against lexical baselines.
- Evaluate graph extraction approaches using shared datasets.
