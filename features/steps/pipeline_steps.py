from __future__ import annotations

import json
from pathlib import Path

from behave import given, then, when

from biblicus.constants import COLLECTION_SCHEMA_VERSION
from biblicus.corpus import Corpus

from features.environment import run_biblicus


def _collection_root(context, name: str) -> Path:
    return (context.workdir / "collections" / name).resolve()


def _write_collection_config(context, name: str) -> None:
    collection_root = _collection_root(context, name)
    collection_root.mkdir(parents=True, exist_ok=True)
    config_path = collection_root / "metadata" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": COLLECTION_SCHEMA_VERSION,
        "created_at": "2026-02-20T00:00:00Z",
        "collection_name": name,
        "source": {
            "kind": "azure-blob",
            "profile": "demo-profile",
            "container": name,
            "prefix": "",
        },
        "discovery": {"mode": "subfolder", "depth": 1, "include_root_files": False},
        "corpus_root": f"corpora/{name}",
        "auto_create": True,
        "deletion_policy": "archive",
    }
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_source_profile(context) -> None:
    import yaml

    path = Path(context.workdir) / ".biblicus" / "config.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sources": [
            {
                "name": "demo-profile",
                "kind": "azure-blob",
                "connection_string": "UseDevelopmentStorage=true",
                "account_name": "acct",
            }
        ]
    }
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")


def _ensure_corpus(context, path: Path) -> None:
    corpus = Corpus.init(path, force=True)
    sample_path = path / "sample.txt"
    sample_path.write_text("alpha", encoding="utf-8")
    corpus.reindex()


@given('a collection "{name}" exists with corpora:')
def step_collection_exists_with_corpora(context, name: str) -> None:
    _write_source_profile(context)
    _write_collection_config(context, name)
    corpus_root = Path(context.workdir) / "corpora" / name
    for row in context.table:
        corpus_path = corpus_root / row["name"]
        _ensure_corpus(context, corpus_path)


@given('a pipeline recipe exists at "{recipe_path}" targeting collection "{collection}" selector "{selector}"')
def step_pipeline_recipe_exists(context, recipe_path: str, collection: str, selector: str) -> None:
    recipe = Path(context.workdir) / recipe_path
    recipe.parent.mkdir(parents=True, exist_ok=True)
    extraction_recipe = Path(context.workdir) / "configs" / "recipes" / "extract.yml"
    extraction_recipe.parent.mkdir(parents=True, exist_ok=True)
    extraction_recipe.write_text(
        """extractor_id: pass-through-text\nconfiguration: {}\n""",
        encoding="utf-8",
    )
    retrieval_config = Path(context.workdir) / "configs" / "retrieval" / "scan.yml"
    retrieval_config.parent.mkdir(parents=True, exist_ok=True)
    retrieval_config.write_text("snippet_characters: 200\n", encoding="utf-8")
    recipe.write_text(
        f"""corpus:\n  collection: {collection}\n  selector: \"{selector}\"\n\nextraction:\n  recipe: {extraction_recipe.as_posix()}\n\nretrieval:\n  retriever: scan\n  configuration: {retrieval_config.as_posix()}\n""",
        encoding="utf-8",
    )


@given('a pipeline recipe exists at "{recipe_path}" with analysis steps')
def step_pipeline_recipe_with_analysis(context, recipe_path: str) -> None:
    recipe = Path(context.workdir) / recipe_path
    recipe.parent.mkdir(parents=True, exist_ok=True)
    extraction_recipe = Path(context.workdir) / "configs" / "recipes" / "extract.yml"
    extraction_recipe.parent.mkdir(parents=True, exist_ok=True)
    extraction_recipe.write_text(
        """extractor_id: pass-through-text\nconfiguration: {}\n""",
        encoding="utf-8",
    )
    retrieval_config = Path(context.workdir) / "configs" / "retrieval" / "scan.yml"
    retrieval_config.parent.mkdir(parents=True, exist_ok=True)
    retrieval_config.write_text("snippet_characters: 200\n", encoding="utf-8")
    analysis_config = Path(context.workdir) / "configs" / "analysis" / "profiling.yml"
    analysis_config.parent.mkdir(parents=True, exist_ok=True)
    analysis_config.write_text("{}\n", encoding="utf-8")
    recipe.write_text(
        f"""corpus:\n  path: corpora/nexus/catalyst\n\nextraction:\n  recipe: {extraction_recipe.as_posix()}\n\nretrieval:\n  retriever: scan\n  configuration: {retrieval_config.as_posix()}\n\nanalysis:\n  - kind: profiling\n    configuration: {analysis_config.as_posix()}\n""",
        encoding="utf-8",
    )
    corpus_root = Path(context.workdir) / "corpora" / "nexus" / "catalyst"
    if corpus_root.exists():
        corpus = Corpus.open(corpus_root)
        sample_path = corpus_root / "sample.txt"
        if not sample_path.exists():
            sample_path.write_text("alpha", encoding="utf-8")
        corpus.reindex()


@when('I run the pipeline recipe "{recipe_path}"')
def step_run_pipeline_recipe(context, recipe_path: str) -> None:
    recipe = Path(context.workdir) / recipe_path
    result = run_biblicus(
        context,
        ["pipeline", "run", "--recipe", str(recipe)],
        extra_env=getattr(context, "extra_env", None),
    )
    context.last_result = result
    assert result.returncode == 0, result.stderr


@then('the extraction snapshot for corpus "{corpus_path}" is built')
def step_extraction_snapshot_built(context, corpus_path: str) -> None:
    corpus_root = Path(context.workdir) / corpus_path
    latest_path = corpus_root / "extracted" / "pipeline" / "latest.json"
    assert latest_path.is_file(), f"Missing extraction snapshot at {latest_path}"


@then('the retrieval snapshot for corpus "{corpus_path}" is built')
def step_retrieval_snapshot_built(context, corpus_path: str) -> None:
    corpus_root = Path(context.workdir) / corpus_path
    latest_path = corpus_root / "retrieval" / "scan" / "latest.json"
    assert latest_path.is_file(), f"Missing retrieval snapshot at {latest_path}"


@then('the profiling analysis output exists for corpus "{corpus_path}"')
def step_profiling_analysis_output(context, corpus_path: str) -> None:
    corpus_root = Path(context.workdir) / corpus_path
    latest_path = corpus_root / "analysis" / "profiling" / "latest.json"
    assert latest_path.is_file(), f"Missing profiling analysis at {latest_path}"
