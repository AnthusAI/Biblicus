# Pipeline recipes

Pipeline recipes define a full information pipeline in one YAML file. A recipe declares the target corpus (or a
collection selector), extraction recipe, retrieval configuration, and analysis runs.

## Example recipe
```yaml
corpus:
  collection: nexus
  selector: "catalyst*"

mirror:
  collection: collections/nexus

extraction:
  recipe: corpora/nexus/catalyst/recipes/extraction/default.yml

retrieval:
  retriever: sqlite-full-text-search
  configuration: configurations/retrieval/fts.yml

analysis:
  - kind: topics
    configuration: configurations/topic-modeling/base.yml
```

## Run a recipe
```
python -m biblicus pipeline run --recipe pipelines/catalyst.yml
```

## Notes
- Mirroring is one-way. Remote sources are authoritative.
- Extraction and retrieval are explicit and reproducible.
