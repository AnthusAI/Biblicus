# Typed application programming interface

Papyrus calls Biblicus through typed Python functions in `biblicus.api` or through the command line. Both routes share one contract: each command has a Pydantic request model, a Pydantic response model, and a plain function that takes the request and returns the response. The command-line interface is a thin wrapper. It parses arguments into the request model, calls the function, and prints the response model as JSON, so the JSON a command prints is exactly the response model.

## Calling a command from Python

```python
from biblicus.api import ReindexRequest, reindex, validate_request

request = validate_request(ReindexRequest, "reindex", corpus_path="corpora/notes")
response = reindex(request)
print(response.model_dump_json(indent=2))
```

`validate_request` turns a Pydantic validation failure into one `ValueError` that names every offending field, for example `Invalid taxonomy discover request: classifier_id: String should have at least 1 character`. The command line prints the same message and exits with status 2.

Requests reject unknown fields, so a misspelled field is reported instead of ignored. Requests carry explicit references. Where a command needs an extraction snapshot, the request takes `extraction_snapshot` as an `extractor_id:snapshot_id` reference; the function never builds or guesses one. The command line keeps its convenience of reusing or building the default extraction snapshot and passes the resolved reference to the function. `query` likewise never builds a snapshot: it uses `snapshot_id` or the corpus latest snapshot and fails clearly when neither exists, while the command line still offers `--auto-deps` and `--no-deps`.

## Commands

| Command | Request model | Response model | Python function |
| --- | --- | --- | --- |
| `taxonomy record` | `TaxonomyRecordRequest` | `TaxonomyRecordOutput` | `taxonomy_record` |
| `taxonomy discover` | `TaxonomyDiscoverRequest` | `TaxonomyDiscoveryOutput` | `taxonomy_discover` |
| `steering export` | `SteeringExportRequest` | `SteeringExportBundle` | `steering_export` |
| `steering artifacts` | `SteeringArtifactsRequest` | `SteeringArtifactInventory` | `steering_artifacts` |
| `steering graph-signals` | `SteeringGraphSignalsRequest` | `SteeringProposalBundle` | `steering_graph_signals` |
| `steering render-seed-manifest` | `SteeringRenderSeedManifestRequest` | `SteeringRenderSeedManifestOutput` | `steering_render_seed_manifest` |
| `topic-classifier train` | `TopicClassifierTrainRequest` | `TopicClassifierTrainOutput` | `topic_classifier_train` |
| `topic-classifier project` | `TopicClassifierProjectRequest` | `TopicClassifierProjectionOutput` | `topic_classifier_project` |
| `analyze topic-context` | `TopicContextRequest` | `TopicContextOutput` | `analyze_topic_context` |
| `analyze topic-trends` | `TopicTrendsRequest` | `TopicTrendOutput` | `analyze_topic_trends` |
| `context-pack build-blocks` | `ContextBlockBuildRequest` | `ContextBlockBuildResult` | `context_pack_build_blocks` |
| `summarize map-reduce` | `SummarizeMapReduceRequest` | `TransformResult` | `summarize_map_reduce` |
| `extract url-text` | `UrlTextRequest` | `UrlTextResponse` | `extract_url_text` |
| `extract article-text` | `ArticleInput` | `TransformResult` | `extract_article_text` |
| `extract web-metadata` | `WebMetadataRequest` | `WebMetadataResponse` | `extract_web_metadata` |
| `query` | `QueryRequest` | `RetrievalResult` | `query` |
| `reindex` | `ReindexRequest` | `ReindexResponse` | `reindex` |
| `graph extract` | `GraphExtractRequest` | `GraphSnapshotManifest` | `graph_extract` |

Where a library function already returned a Pydantic model, that model is the response model. The `--format markdown` renderings of `taxonomy discover`, `topic-classifier project`, `analyze topic-context` and `analyze topic-trends` are command-line presentations of the same response model.

The `extract url-text` and `extract web-metadata` commands read their JSON input from `--input-json`, and `extract article-text` and `summarize map-reduce` read theirs the same way. Their failure contract is unchanged: structured failures print a `status: failed` object to standard error and exit with a nonzero status.

## Published JSON Schemas

Every request and response has a JSON Schema in `docs/api-schemas`, named `<command>.request.schema.json` and `<command>.response.schema.json`, for example `taxonomy-discover.response.schema.json`. Response schemas use serialization mode, so they describe exactly the JSON the command prints. The schemas are generated from the models:

```bash
python scripts/generate_api_schemas.py
python scripts/generate_api_schemas.py --check
```

The first form rewrites the files. The second exits with status 1 and lists every missing, changed or unexpected file, and the behavior specifications run the same check, so a model change cannot ship without regenerated schemas.

## Specifications

`features/api_contract.feature` proves that the published schemas match the models, that drift is reported and repaired, that Python functions return the typed responses, and that invalid requests name each offending field. Each command group also proves in its own feature that the real command-line output validates against its published schema: taxonomy in `features/taxonomy_ontology.feature`, steering in `features/api_contract.feature` and `features/taxonomy_ontology.feature`, topic classifier in `features/topic_classifier.feature`, analysis in `features/topic_trends.feature` and `features/topic_context.feature`, graph in `features/graph_extraction.feature`, bounded web transforms in `features/bounded_web_transform.feature`, and retrieval, reindex, context-pack blocks and web metadata in `features/api_contract.feature`.
