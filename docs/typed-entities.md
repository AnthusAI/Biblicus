# Typed entities and relations

A publication has its own idea of what matters: makers, models, licences, tasks, datasets. `spaCy` labels such as `ORG` and `PERSON` do not say that. The typed-entity extractor reads the extracted text of corpus items and returns entities and relations whose kinds and types come from a **closed vocabulary that you supply**. Biblicus never hard-codes a kind.

Every entity and relation carries its evidence: the item identifier and character offsets into the item text. Nothing is published or accepted here. An entity is either `resolved` to something the desk already accepted, or `proposed` for the desk to review; deciding which proposals to accept belongs to the consumer.

The backend was chosen by an evaluation, see [Typed extractor evaluation](typed-extractor-evaluation.md). No language model is involved.

## Install

The default backend uses the GLiNER2 span model. Its dependencies (PyTorch and Transformers) are heavy, so they live behind an optional extra:

```bash
pip install "biblicus[typed-extraction]"
```

Without the extra, `--backend registry-only` still works and `--backend gliner2` fails with an error that names the extra. The model, `fastino/gliner2-base-v1` at revision `f9634218e53580c56edf0de97ca1a7d3f1c2354e` (Apache-2.0), downloads from Hugging Face on first use and then runs on the CPU. Run the command as a job, not inside a Lambda bundle: the model needs about 2 GB of memory.

## Run it

Build an extraction snapshot first, because the extractor reads extracted text:

```bash
biblicus extract build --corpus corpora/shipped --stage pass-through-text
biblicus extract typed-entities \
  --corpus corpora/shipped \
  --vocabulary vocabulary.yml \
  --registry registry.json \
  --out out/
```

| Option | Meaning |
| --- | --- |
| `--corpus` | Corpus to read. Defaults to the corpus found from the working directory. |
| `--vocabulary` | Closed vocabulary file (required). |
| `--registry` | Accepted entities. Without it every mention is proposed. |
| `--backend` | `gliner2` (default): registry matcher first, then GLiNER2. `registry-only`: registry matcher alone. |
| `--threshold` | Score threshold for the model, greater than 0 and at most 1. Default `0.7`. |
| `--item-id` | Item to process. Repeat for several. Default: every item that has extracted text. |
| `--extraction-snapshot` | `extractor_id:snapshot_id` supplying the text. Default: the latest extraction snapshot. |
| `--out` | Directory that also receives `output.json`. |

Standard output is the output document. The same document is always written to the corpus, so `--out` is only for handing it to another system.

## The vocabulary

A YAML (or JSON) file with the entity kinds and relation types of one publication. `label` is the only instruction the model receives for a kind or type, so keep it short and natural. `description` is for human readers.

```yaml
version: 1
publication: shipped
entity_kinds:
  - key: maker
    label: company or developer
  - key: model
    label: AI model
  - key: licence
    label: software licence
relation_types:
  - key: made_by
    label: made by
  - key: licensed_under
    label: licensed under
```

A vocabulary can hold both `model` (a specific named model, such as `CosyVoice2` or `CosyVoice 3`) and `model_family` (the line of models above it, such as `CosyVoice`). They are separate kinds and the extractor never folds one into the other. To relate a model to its family, add a `member_of` relation type (see `datasets/typed_extraction_lab/vocabulary.yml`). The model proposes `member_of` only when the text states the membership; a shared name prefix does not make one, and a model whose family the text does not name has no `member_of` relation.

Keys and labels must be unique inside their group. Every `kind` and `type` in the output is a key from this file. A complete example is `datasets/typed_extraction_lab/vocabulary.yml`.

## The registry

A JSON list of accepted entities. `aliases` are the surface forms that identify the entity:

```json
[
  {"key": "accuknox-inc", "kind": "maker", "aliases": ["AccuKnox Inc.", "AccuKnox"]},
  {"key": "apache-2-0", "kind": "licence", "aliases": ["Apache 2.0"]}
]
```

The extractor rejects a registry whose `kind` is outside the vocabulary, whose alias is empty after normalisation, or whose alias belongs to two different entities. The key itself is not an alias; list it if it should match.

## How a mention is resolved

1. **Registry matcher.** Every alias is searched in the item text. Aliases compare equal after normalisation: letters are lower-cased and every run of characters that is not a letter or digit counts as one space, so `NAME-A`, `name a`, `Name   A` and `NAME_A` are the same alias. A match must cover whole words. `Gemma 3` does not match inside `Gemma-3-4B-it`, and `Qwen3` does not match inside `Qwen3.5-4B`: a text that continues into a longer name is a different mention. The longest alias wins where aliases overlap.
2. **Model.** The model proposes spans for the remaining text. A span that overlaps a registry match is dropped. A span whose whole normalised text equals an alias of the same kind also resolves; anything else is `proposed`.

Resolution is never fuzzy and never by prefix. A mention that matches no alias exactly is a `proposed` entity, however similar it looks to a known one. Merging two entities is a decision for the desk.

## Relations

Relations come from the model only; the registry matcher does not extract them. Both endpoints must be entities of the same item: an endpoint is the entity whose span overlaps the model's endpoint by at least half, and a relation with an endpoint that is not an entity is dropped. A relation is `resolved` only when both endpoints are `resolved`; otherwise it is `proposed`. The evaluation found relations less reliable than entities (relation F1 56 against 80 for a language model), which is why a relation with a proposed endpoint stays a proposal.

## Output

Standard output, and `output.json`, is one document: a `TypedEntitiesOutput`. The published schema is `docs/api-schemas/extract-typed-entities.response.schema.json`; the request schema is `extract-typed-entities.request.schema.json`.

```json
{
  "backend": {"id": "gliner2", "model": "fastino/gliner2-base-v1", "revision": "f9634218e53580c56edf0de97ca1a7d3f1c2354e", "threshold": 0.7},
  "items": [
    {
      "entities": [
        {"entity_key": "accuknox inc", "id": "e1", "kind": "maker", "score": 1.0,
         "span": {"end": 12, "start": 0}, "state": "resolved", "text": "AccuKnox Inc"},
        {"entity_key": "guard 1 1", "id": "e2", "kind": "model", "score": 1.0,
         "span": {"end": 32, "start": 23}, "state": "resolved", "text": "Guard 1.1"}
      ],
      "item_id": "item-0h",
      "relations": [
        {"id": "r1", "object": "e1", "score": 0.9754, "span": {"end": 32, "start": 0},
         "state": "resolved", "subject": "e2", "type": "made_by"}
      ]
    }
  ],
  "schema_version": 1,
  "summary": {"entities": 2, "items": 1, "proposed": 0, "relations": 1, "resolved": 2},
  "vocabulary": {"hash": "...", "publication": "shipped", "version": 1}
}
```

(Keys are sorted; the example is shortened.) `span` offsets are character offsets into the extracted text of the item, `entities` are ordered by position, and `entity_key` is set exactly when `state` is `resolved`. A registry match scores `1.0`. A relation `span` covers both endpoints. A trailing full stop is not part of a span, so the alias `AccuKnox Inc.` matches the text `AccuKnox Inc.` as the span `AccuKnox Inc`.

## Determinism and the cache

The output has no timestamps: the same text, vocabulary, registry and settings always produce byte-identical output. What the model returns for a text is cached under

```text
analysis/typed-entities/cache/<key>.json
```

where the key is the hash of the text hash, vocabulary hash, backend, model, model revision and threshold. A second run with the same inputs reads the cache, never loads the model, and prints identical output. The cache holds the model's raw proposals, so changing the registry changes the resolution without calling the model again, while changing the vocabulary, the threshold or the text calls it again.

Each run is stored under a run identifier derived from all of its inputs:

```text
analysis/typed-entities/<run id>/output.json      the output document
analysis/typed-entities/<run id>/metadata.json    when it ran, elapsed seconds, backend calls, cache hits, file paths
```

`metadata.json` is where anything that varies between executions lives.

## Python

```python
from biblicus.api import TypedEntitiesRequest, extract_typed_entities

output = extract_typed_entities(
    TypedEntitiesRequest(
        corpus_path="corpora/shipped",
        vocabulary_path="vocabulary.yml",
        registry_path="registry.json",
    )
)
```

The extractor depends only on `biblicus.typed_extraction_backends.TypedExtractionBackend`. A different backend implements `extract(text, vocabulary, threshold)` and returns character offsets; it is passed to `biblicus.typed_extraction.extract_typed_entities` directly.

## Try it on the lab dataset

`datasets/typed_extraction_lab/` holds 142 public documents, a vocabulary and gold labels. `prepare_corpus.py` turns them into a corpus and builds a registry from half of the gold labels:

```bash
python scripts/typed_extraction_evaluation/prepare_corpus.py --out /tmp/typed-real
biblicus extract typed-entities --corpus /tmp/typed-real/corpus \
  --vocabulary datasets/typed_extraction_lab/vocabulary.yml \
  --registry /tmp/typed-real/registry.json --backend gliner2 --out /tmp/typed-real/out
```

The specifications are `features/typed_entity_extraction.feature`, which runs against a fake GLiNER2 library, and `features/typed_entity_extraction_integration.feature`, which runs the pinned model when it is already in the local Hugging Face cache.
