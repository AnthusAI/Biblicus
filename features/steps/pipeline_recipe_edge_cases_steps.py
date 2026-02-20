from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from behave import then, when
from pydantic import BaseModel, ValidationError

from biblicus.collections import init_collection
from biblicus.constants import COLLECTION_SCHEMA_VERSION
from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.models import (
    PipelineAnalysisConfig,
    PipelineCorpusSelector,
    PipelineRecipeConfig,
    PipelineRetrievalConfig,
    RemoteCorpusCollectionConfig,
    RemoteCorpusCollectionDiscovery,
    RemoteCorpusSourceConfig,
)
from biblicus.pipelines import (
    _normalize_extraction_configuration,
    _resolve_collection_corpus_root,
    _resolve_collection_root,
    _resolve_target_corpora,
    _run_analysis,
    _run_retrieval,
    load_pipeline_recipe,
    run_pipeline_recipe,
)
from biblicus.user_config import (
    BiblicusUserConfig,
    SourceProfileConfig,
    _parse_account_name_from_connection_string,
    resolve_source_profile,
)


class _FakePlan:
    def __init__(self, status: str, reason: str | None = None) -> None:
        self.status = status
        self.root = SimpleNamespace(reason=reason)

    def execute(self, *, mode: str, handler_registry) -> None:
        _ = mode
        _ = handler_registry


class _FakeAnalysisBackend:
    def __init__(self, error: ValidationError) -> None:
        self._error = error

    def run_analysis(self, *args, **kwargs):
        raise self._error


@when("I exercise pipeline recipe edge cases")
def step_exercise_pipeline_recipe_edge_cases(context) -> None:
    workdir = Path(context.workdir)
    try:
        SourceProfileConfig(name="bad", kind="gcs")
        raise AssertionError("Expected invalid source profile kind to fail")
    except ValueError:
        pass

    try:
        resolve_source_profile("")
        raise AssertionError("Expected empty profile name to fail")
    except ValueError:
        pass

    try:
        resolve_source_profile("missing", config=BiblicusUserConfig())
        raise AssertionError("Expected missing profile to fail")
    except ValueError:
        pass

    azure_profile = SourceProfileConfig(
        name="azure",
        kind="azure-blob",
        connection_string="DefaultEndpointsProtocol=https;AccountName=acct;AccountKey=key;",
    )
    resolved = resolve_source_profile("azure", config=BiblicusUserConfig(sources=[azure_profile]))
    assert resolved.account_name == "acct", "Expected account name from connection string"

    try:
        resolve_source_profile(
            "azure-missing",
            config=BiblicusUserConfig(
                sources=[
                    SourceProfileConfig(
                        name="azure-missing", kind="azure-blob", account_name="acct"
                    )
                ]
            ),
        )
        raise AssertionError("Expected missing Azure credentials to fail")
    except ValueError:
        pass

    assert (
        _parse_account_name_from_connection_string("AccountKey=key;") is None
    ), "Expected missing AccountName to return None"

    try:
        RemoteCorpusCollectionDiscovery.model_validate({"mode": "invalid", "depth": 1})
        raise AssertionError("Expected invalid discovery mode to fail")
    except ValueError:
        pass

    try:
        PipelineCorpusSelector.model_validate(
            {"path": "corpus", "collection": "demo", "selector": "*"}
        )
        raise AssertionError("Expected selector with both path and collection to fail")
    except ValueError:
        pass

    try:
        PipelineCorpusSelector.model_validate({})
        raise AssertionError("Expected selector with no target to fail")
    except ValueError:
        pass

    try:
        PipelineCorpusSelector.model_validate({"collection": "demo"})
        raise AssertionError("Expected selector without pattern to fail")
    except ValueError:
        pass

    valid_source = RemoteCorpusSourceConfig(
        kind="s3",
        profile="profile",
        bucket="demo",
        prefix="",
    )
    try:
        RemoteCorpusCollectionConfig.model_validate(
            {
                "schema_version": 99,
                "created_at": "2026-02-20T00:00:00Z",
                "collection_name": "demo",
                "source": valid_source.model_dump(),
                "discovery": {"mode": "subfolder", "depth": 1, "include_root_files": False},
                "corpus_root": "corpora/demo",
                "auto_create": True,
                "deletion_policy": "archive",
            }
        )
        raise AssertionError("Expected invalid schema version to fail")
    except ValueError:
        pass

    try:
        RemoteCorpusCollectionConfig.model_validate(
            {
                "schema_version": COLLECTION_SCHEMA_VERSION,
                "created_at": "2026-02-20T00:00:00Z",
                "collection_name": "demo",
                "source": valid_source.model_dump(),
                "discovery": {"mode": "subfolder", "depth": 1, "include_root_files": False},
                "corpus_root": "corpora/demo",
                "auto_create": True,
                "deletion_policy": "unknown",
            }
        )
        raise AssertionError("Expected invalid deletion policy to fail")
    except ValueError:
        pass

    missing_recipe = workdir / "missing.yml"
    try:
        load_pipeline_recipe(missing_recipe)
        raise AssertionError("Expected missing recipe to fail")
    except FileNotFoundError:
        pass

    invalid_recipe = workdir / "invalid.yml"
    invalid_recipe.write_text("- not-a-mapping\n", encoding="utf-8")
    try:
        load_pipeline_recipe(invalid_recipe)
        raise AssertionError("Expected non-mapping recipe to fail")
    except ValueError:
        pass

    recipe_with_mirror = workdir / "mirror.yml"
    corpus_path = workdir / "corpus"
    Corpus.init(corpus_path, force=True)
    collection_path = workdir / "collections" / "demo"
    collection_path.mkdir(parents=True, exist_ok=True)
    recipe_with_mirror.write_text(
        f"corpus:\n  path: {corpus_path.as_posix()}\n"
        f"mirror:\n  collection: {collection_path.as_posix()}\n",
        encoding="utf-8",
    )
    import biblicus.pipelines as pipelines_module

    original_pull = pipelines_module.pull_collection
    pipelines_module.pull_collection = lambda _: None
    try:
        result = run_pipeline_recipe(recipe_with_mirror)
        assert str(corpus_path.resolve()) in result.corpora, "Mirror run missing corpus path"
    finally:
        pipelines_module.pull_collection = original_pull

    existing_collection_root = workdir / "collections" / "demo"
    existing_collection_root.mkdir(parents=True, exist_ok=True)
    assert (
        _resolve_collection_root(str(existing_collection_root)) == existing_collection_root
    ), "Expected collection root to resolve existing path"

    collection_root = workdir / "collections" / "empty"
    collection_root.mkdir(parents=True, exist_ok=True)
    collection_config = RemoteCorpusCollectionConfig(
        schema_version=COLLECTION_SCHEMA_VERSION,
        created_at="2026-02-20T00:00:00Z",
        collection_name="empty",
        source=valid_source,
        discovery=RemoteCorpusCollectionDiscovery(mode="subfolder", depth=1, include_root_files=False),
        corpus_root="corpora/missing",
        auto_create=True,
        deletion_policy="archive",
    )
    init_collection(collection_root, collection_config)
    recipe_config = PipelineRecipeConfig(
        corpus=PipelineCorpusSelector(collection=str(collection_root), selector="*"),
        mirror=None,
        extraction=None,
        retrieval=None,
        analysis=None,
    )
    try:
        _resolve_target_corpora(recipe_config)
        raise AssertionError("Expected missing corpus root to fail")
    except FileNotFoundError:
        pass

    corpus_root = workdir / "corpora" / "demo"
    corpus_root.mkdir(parents=True, exist_ok=True)
    (corpus_root / "_skip.txt").write_text("x", encoding="utf-8")
    (corpus_root / ".hidden").mkdir(parents=True, exist_ok=True)
    (corpus_root / "keep").mkdir(parents=True, exist_ok=True)
    collection_root = workdir / "collections" / "demo"
    collection_config = RemoteCorpusCollectionConfig(
        schema_version=COLLECTION_SCHEMA_VERSION,
        created_at="2026-02-20T00:00:00Z",
        collection_name="demo",
        source=valid_source,
        discovery=RemoteCorpusCollectionDiscovery(mode="subfolder", depth=1, include_root_files=False),
        corpus_root="corpora/demo",
        auto_create=True,
        deletion_policy="archive",
    )
    init_collection(collection_root, collection_config)
    recipe_config = PipelineRecipeConfig(
        corpus=PipelineCorpusSelector(collection=str(collection_root), selector="keep"),
        mirror=None,
        extraction=None,
        retrieval=None,
        analysis=None,
    )
    resolved_corpora = [path.resolve() for path in _resolve_target_corpora(recipe_config)]
    expected_corpus = (corpus_root / "keep").resolve()
    assert expected_corpus in resolved_corpora, f"Selector mismatch: {resolved_corpora}"

    absolute_root = workdir / "absolute"
    assert (
        _resolve_collection_corpus_root(workdir / "not-collections", str(absolute_root))
        == absolute_root
    ), "Expected absolute corpus root to pass through"

    try:
        _normalize_extraction_configuration({"configuration": []})
        raise AssertionError("Expected invalid extraction configuration to fail")
    except ValueError:
        pass

    try:
        _normalize_extraction_configuration({"extractor_id": "", "configuration": {}})
        raise AssertionError("Expected empty extractor_id to fail")
    except ValueError:
        pass

    try:
        _normalize_extraction_configuration({"max_workers": True, "configuration": {}})
        raise AssertionError("Expected boolean max_workers to fail")
    except ValueError:
        pass

    try:
        _normalize_extraction_configuration({"max_workers": "no", "configuration": {}})
        raise AssertionError("Expected invalid max_workers to fail")
    except ValueError:
        pass

    try:
        _normalize_extraction_configuration({"max_workers": 0, "configuration": {}})
        raise AssertionError("Expected max_workers < 1 to fail")
    except ValueError:
        pass

    extractor_id, config, workers = _normalize_extraction_configuration(
        {"extractor_id": "pass-through-text", "configuration": {}}
    )
    assert extractor_id == "pipeline", "Expected pipeline wrapper for non-pipeline extractor"
    assert (
        config["stages"][0]["extractor_id"] == "pass-through-text"
    ), "Expected stage extractor id"
    assert workers is None, "Expected max_workers to remain None"

    retrieval_config_path = workdir / "retrieval.yml"
    retrieval_config_path.write_text("snippet_characters: 100\n", encoding="utf-8")
    retrieval_config = PipelineRetrievalConfig(
        retriever="scan", configuration=str(retrieval_config_path)
    )

    original_build_plan = pipelines_module.build_plan_for_index

    pipelines_module.build_plan_for_index = lambda *args, **kwargs: _FakePlan(
        "blocked", "blocked"
    )
    try:
        _run_retrieval(Corpus.open(corpus_path), retrieval_config)
        raise AssertionError("Expected blocked retrieval plan to fail")
    except ValueError:
        pass

    pipelines_module.build_plan_for_index = lambda *args, **kwargs: _FakePlan("ready")
    try:
        _run_retrieval(Corpus.open(corpus_path), retrieval_config)
    finally:
        pipelines_module.build_plan_for_index = original_build_plan

    analysis_config_path = workdir / "analysis.yml"
    analysis_config_path.write_text("{}\n", encoding="utf-8")
    analysis_configs = [
        PipelineAnalysisConfig(kind="profiling", configuration=str(analysis_config_path))
    ]
    no_snapshot_corpus = Corpus.init(workdir / "nosnap", force=True)
    try:
        _run_analysis(no_snapshot_corpus, analysis_configs, None)
        raise AssertionError("Expected analysis without snapshot to fail")
    except ValueError:
        pass

    class _DummyModel(BaseModel):
        name: str

    try:
        _DummyModel.model_validate({})
    except ValidationError as exc:
        validation_error = exc
    else:
        raise AssertionError("Expected validation error")

    corpus_for_analysis = Corpus.open(corpus_path)
    sample_path = corpus_for_analysis.root / "sample.txt"
    if not sample_path.exists():
        sample_path.write_text("alpha", encoding="utf-8")
        corpus_for_analysis.reindex()
    build_extraction_snapshot(
        corpus_for_analysis,
        extractor_id="pipeline",
        configuration_name="default",
        configuration={"stages": [{"extractor_id": "pass-through-text", "config": {}}]},
        max_workers=1,
    )
    extraction_ref = corpus_for_analysis.latest_extraction_snapshot_reference()
    assert extraction_ref is not None, "Expected extraction snapshot reference"

    original_backend = pipelines_module.get_analysis_backend
    pipelines_module.get_analysis_backend = lambda _: _FakeAnalysisBackend(validation_error)
    try:
        _run_analysis(corpus_for_analysis, analysis_configs, extraction_ref)
        raise AssertionError("Expected analysis validation error to propagate")
    except ValueError:
        pass
    finally:
        pipelines_module.get_analysis_backend = original_backend


@then("the pipeline recipe edge cases succeed")
def step_pipeline_recipe_edge_cases_done(context) -> None:
    assert context is not None
