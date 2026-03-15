# PR-FAQ: Default Extraction Recipe for Analysis Runs (Draft)

## Press Release

Today we are introducing a default extraction recipe convention for Biblicus analyses. When an analysis run needs extracted text and no snapshot is provided, Biblicus automatically loads `corpora/<Corpus>/recipes/extraction/default.yml` and builds the required extraction snapshot if it is missing. This removes the need to look up snapshot IDs for everyday workflows while keeping the extraction pipeline explicit and reproducible through recipe files.

This change standardizes where extraction recipes live, encourages corpus-local configuration, and preserves the snapshot artifact layout under `extracted/` and `analysis/` so downstream tooling remains consistent.

## FAQ

**Why introduce a default extraction recipe?**
Analyses should be runnable with a single command without copying snapshot IDs. A conventional default recipe keeps the pipeline explicit while enabling “build if missing” behavior.

**Where does Biblicus look for the recipe?**
`corpora/<Corpus>/recipes/extraction/default.yml`.

**What happens if the recipe is missing?**
If a snapshot is already available, Biblicus falls back to the latest snapshot with a reproducibility warning. If no snapshot exists, the command fails with clear guidance to add a recipe or pass `--extraction-snapshot`.

**How is the snapshot identity determined?**
The snapshot ID is derived from the extraction configuration and the current catalog generation timestamp, matching the existing extraction snapshot identity rules.

**How do I force a different extraction pipeline?**
Create or select a different extraction recipe file and pass an explicit snapshot ID, or run `biblicus extract build` with that recipe to produce a new snapshot and then reference it.

**How do I reset or rebuild?**
Delete the snapshot directory under `extracted/<extractor_id>/<snapshot_id>` and rerun the analysis, or run `biblicus extract build --force` for the configured recipe.
