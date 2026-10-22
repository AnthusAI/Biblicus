# Typed application programming interface

Papyrus calls Biblicus through typed Python functions in `biblicus.api` or through the command line. Both routes share one contract: each command has a Pydantic request model, a Pydantic response model, and a plain function that takes the request and returns the response. The command-line interface is a thin wrapper. It parses arguments into the request model, calls the function, and prints the response model as JSON, so the JSON a command prints is exactly the response model.

## Calling a command from Python

```python
from biblicus.api import ReindexRequest, reindex, validate_request

request = validate_request(ReindexRequest, "reindex", corpus_path="corpora/notes")
response = reindex(request)
print(response.model_dump_json(indent=2))
```

`validate_request` turns a Pydantic validation failure into one `ValueError` that names every offending field, for example `Invalid taxonomy discover request: classifier_id: String should have at least 1 character`. The exception is an `InvalidRequestError`, a `ValueError` subclass, so callers can tell a rejected request from any other failure. The command line reports it as the failure envelope described under Failures.

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
| `analyze topic-identity` | `TopicIdentityRequest` | `TopicIdentityOutput` | `analyze_topic_identity` |
| `context-pack build-blocks` | `ContextBlockBuildRequest` | `ContextBlockBuildResult` | `context_pack_build_blocks` |
| `summarize map-reduce` | `SummarizeMapReduceRequest` | `TransformResult` | `summarize_map_reduce` |
| `extract url-text` | `UrlTextRequest` | `UrlTextResponse` | `extract_url_text` |
| `extract article-text` | `ArticleInput` | `TransformResult` | `extract_article_text` |
| `extract web-metadata` | `WebMetadataRequest` | `WebMetadataResponse` | `extract_web_metadata` |
| `query` | `QueryRequest` | `RetrievalResult` | `query` |
| `reindex` | `ReindexRequest` | `ReindexResponse` | `reindex` |
| `graph extract` | `GraphExtractRequest` | `GraphSnapshotManifest` | `graph_extract` |

Where a library function already returned a Pydantic model, that model is the response model. The `--format markdown` renderings of `taxonomy discover`, `topic-classifier project`, `analyze topic-context`, `analyze topic-trends` and `analyze topic-identity` are command-line presentations of the same response model.

The `extract url-text` and `extract web-metadata` commands read their JSON input from `--input-json`, and `extract article-text` and `summarize map-reduce` read theirs the same way.

## Failures

Every command in the table above fails the same way. It prints exactly one JSON object on standard output, writes nothing else to standard output, and leaves standard error empty:

```json
{
  "status": "failed",
  "error": {
    "code": "invalid_request",
    "message": "Invalid steering export request: classifier_id: String should have at least 1 character",
    "details": {}
  }
}
```

The object is a `CommandFailure` from `biblicus.command_failure`. `code` is a stable machine-readable name, `message` is a sentence for people, and `details` carries structured diagnostics such as `http_status` and is empty when there are none. The exit status separates two cases, and the code alone decides which:

| Code | Exit status | Raised when |
| --- | --- | --- |
| `invalid_request` | 2 | A request model failed validation, a numeric input such as `timeout_seconds` is not a number, stdin is empty where a request is required, or arguments conflict or are missing (`--auto-deps` with `--no-deps`; neither or both of `--all` and `--item-id`; no extraction snapshot for `graph extract`). |
| `invalid_input_json` | 2 | `--input-json` is not JSON or not an object. |
| `missing_source_uri` | 2 | `extract url-text` input has no `source_uri`. |
| `missing_input` | 2 | `extract web-metadata` input has neither `source_uri` nor `html_content`. |
| `invalid_input` | 2 | `extract article-text` or `summarize map-reduce` input or model was rejected. |
| `input_too_large` | 2 | The transform input or request exceeds the size bound. |
| `invalid_configuration` | 2 | The gateway configuration (key, base address, retries) was rejected before the call. |
| `operation_failed` | 1 | Any other `ValueError`, missing file or similar raised while the operation ran, for example a missing snapshot or invalid file contents. |
| `provider_failed`, `invalid_provider_output` | 1 | The gateway call failed or returned unusable output. |
| `web_metadata_failed` | 1 | `extract web-metadata` rejected the page. |
| Codes named by URL extraction, such as `direct_conversion_failed` | 1 | The fetch or conversion failed. |

`details` is never lost. When `extract url-text` fails after running, `details` carries a `UrlTextFailureDetails` (`source_kind`, `strategy`, `content_type`, `prompt_version`, `attempts`) merged with any details the extraction error named, such as `http_status`. When `extract article-text` or `summarize map-reduce` fails after running, `details` carries a `TransformFailureDetails` (`prompt_version`, `model`, `task`, `warnings`, `map_reduce`, `retry_trace`, `retry_failure_count`, `retry_rounds_used`). Failures raised before anything ran, such as `invalid_input_json`, have empty `details`.

A caller therefore reads standard output for both outcomes: parse it as the response model when the exit status is 0 and as `CommandFailure` otherwise. The Python functions keep returning their response models, including the `status` and `error` fields of `UrlTextResponse` and `TransformResult`; only the command line turns a failed response into the envelope, so a failed `extract url-text` and a failed `summarize map-reduce` look the same as a failed `query`.

Two things sit outside the envelope. Argument syntax errors, such as a missing required flag, come from `argparse` as usage text on standard error with exit status 2 before any command runs. And the commands that are not in the table, such as `ingest`, `list` and `extract build`, are written for people: they print the failure message as plain text on standard error and exit with status 2.

## Published JSON Schemas

Every request and response has a JSON Schema in `docs/api-schemas`, named `<command>.request.schema.json` and `<command>.response.schema.json`, for example `taxonomy-discover.response.schema.json`. Response schemas use serialization mode, so they describe exactly the JSON the command prints. The schemas are generated from the models:

```bash
python scripts/generate_api_schemas.py
python scripts/generate_api_schemas.py --check
```

The first form rewrites the files. The second exits with status 1 and lists every missing, changed or unexpected file, and the behavior specifications run the same check, so a model change cannot ship without regenerated schemas.

## Specifications

`features/cli_failure_envelope.feature` proves the failure contract: the envelope on standard output, the exit status for each category, the empty standard error, and that every typed command declares it. `features/api_contract.feature` proves that the published schemas match the models, that drift is reported and repaired, that Python functions return the typed responses, and that invalid requests name each offending field. Each command group also proves in its own feature that the real command-line output validates against its published schema: taxonomy in `features/taxonomy_ontology.feature`, steering in `features/api_contract.feature` and `features/taxonomy_ontology.feature`, topic classifier in `features/topic_classifier.feature`, analysis in `features/topic_trends.feature`, `features/topic_trend_weekly_bins.feature`, `features/topic_identity.feature` and `features/topic_context.feature`, graph in `features/graph_extraction.feature`, bounded web transforms in `features/bounded_web_transform.feature`, and retrieval, reindex, context-pack blocks and web metadata in `features/api_contract.feature`.
