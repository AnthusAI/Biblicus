from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from behave import then, when
from pydantic import BaseModel, ValidationError

from biblicus.collections import init_collection
from biblicus.collections import (
    _archive_missing_corpora,
    _discover_subfolders,
    _join_prefix,
    _partition_tag_resolver,
    _relative_key,
    _resolve_corpus_root,
    _ensure_partition_corpus,
    _ensure_collection_corpus,
    load_collection_config,
    pull_collection,
)
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
from biblicus.evaluation.benchmark_runner import (
    BenchmarkConfig,
    BenchmarkRunner,
    CategoryConfig,
    CategoryResult,
)
from biblicus.cli import (
    cmd_benchmark_download,
    cmd_benchmark_run,
    cmd_benchmark_status,
    cmd_collection_show,
    cmd_graph_extract,
    cmd_source_set,
    cmd_source_show,
    _resolve_extraction_snapshot_for_analysis,
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

    unsupported_profile = SourceProfileConfig.model_construct(
        name="unsupported",
        kind="gcs",
    )
    try:
        resolve_source_profile(
            "unsupported",
            config=BiblicusUserConfig.model_construct(sources=[unsupported_profile]),
        )
        raise AssertionError("Expected unsupported profile kind to fail")
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
    assert (
        _parse_account_name_from_connection_string("AccountName=;AccountKey=key;") is None
    ), "Expected empty AccountName to return None"

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
    from biblicus import pipelines as pipelines_module

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

    missing_collection_root = workdir / "collections" / "missing"
    try:
        load_collection_config(missing_collection_root)
        raise AssertionError("Expected missing collection config to fail")
    except FileNotFoundError:
        pass

    collections_root = workdir / "collections" / "demo"
    assert collections_root.parent.name == "collections"
    resolved_root = _resolve_corpus_root(collections_root, collection_config)
    expected_root = (workdir / "corpora" / "demo").resolve()
    assert resolved_root == expected_root, "Expected corpus root resolution for collections dir"
    non_collection_root = workdir / "not-collections" / "demo"
    resolved_non_collection = _resolve_corpus_root(non_collection_root, collection_config)
    assert resolved_non_collection == (workdir / "not-collections" / "corpora" / "demo").resolve()

    absolute_root = workdir / "absolute"
    resolved_absolute = _resolve_corpus_root(
        workdir / "collections" / "demo",
        collection_config.model_copy(update={"corpus_root": str(absolute_root)}),
    )
    assert resolved_absolute == absolute_root, "Expected absolute corpus root to pass through"

    try:
        _ensure_collection_corpus(
            workdir / "corpora" / "missing",
            collection_name="demo",
            corpus_name="missing",
            source_config=valid_source,
            auto_create=False,
        )
        raise AssertionError("Expected missing corpus with auto_create false to fail")
    except ValueError:
        pass

    existing_corpus_root = workdir / "corpora" / "existing"
    Corpus.init(existing_corpus_root, force=True)
    _ensure_collection_corpus(
        existing_corpus_root,
        collection_name="demo",
        corpus_name="existing",
        source_config=valid_source,
        auto_create=True,
    )

    partition_corpus_root = workdir / "corpora" / "partition"
    _ensure_partition_corpus(
        partition_corpus_root,
        collection_name="partition",
        source_config=valid_source,
    )
    _ensure_partition_corpus(
        partition_corpus_root,
        collection_name="partition",
        source_config=valid_source,
    )

    class _FakeSource:
        def __init__(self, keys):
            self._keys = keys

        def list_items(self):
            return [SimpleNamespace(key=item) for item in self._keys]

    fake_source = _FakeSource(
        [
            "prefix",
            "prefix/root.txt",
            "prefix/folder-c/file4.txt",
            "prefix/folder-c/sub/file5.txt",
        ]
    )
    discovered = _discover_subfolders(
        fake_source,
        RemoteCorpusSourceConfig(
            kind="s3",
            profile="profile",
            bucket="demo",
            prefix="prefix",
        ),
        RemoteCorpusCollectionDiscovery(mode="subfolder", depth=1, include_root_files=False),
    )
    assert "folder-c" in discovered, "Expected prefix-relative subfolder discovery"

    resolver = _partition_tag_resolver()
    assert resolver("") == [], "Expected empty key to yield no tags"
    assert resolver("table") == [], "Expected single segment to yield no tags"
    assert resolver("table/row.json") == ["table:table"], "Expected tag from partition resolver"

    assert _relative_key("prefix/path/file.txt", "prefix") == "path/file.txt"
    assert _join_prefix("prefix", "child") == "prefix/child/"

    archive_root = workdir / "corpora" / "archive"
    (archive_root / "keep").mkdir(parents=True, exist_ok=True)
    (archive_root / "remove").mkdir(parents=True, exist_ok=True)
    (archive_root / ".archived").mkdir(parents=True, exist_ok=True)
    (archive_root / "note.txt").write_text("skip", encoding="utf-8")
    archived = _archive_missing_corpora(
        archive_root, ["keep"], deletion_policy="archive"
    )
    assert archived == 1, "Expected one corpus archived"
    assert (archive_root / ".archived").exists(), "Expected archive directory to exist"

    missing_root = workdir / "corpora" / "missing-root"
    assert (
        _archive_missing_corpora(missing_root, ["keep"], deletion_policy="archive") == 0
    ), "Expected zero archives for missing corpus root"

    delete_root = workdir / "corpora" / "delete"
    (delete_root / "keep").mkdir(parents=True, exist_ok=True)
    (delete_root / "remove").mkdir(parents=True, exist_ok=True)
    deleted = _archive_missing_corpora(
        delete_root, ["keep"], deletion_policy="delete"
    )
    assert deleted == 1, "Expected one corpus deleted"

    mismatch_collection_root = workdir / "collections" / "mismatch"
    mismatch_config = RemoteCorpusCollectionConfig(
        schema_version=COLLECTION_SCHEMA_VERSION,
        created_at="2026-02-20T00:00:00Z",
        collection_name="mismatch",
        source=valid_source,
        discovery=RemoteCorpusCollectionDiscovery(mode="subfolder", depth=1, include_root_files=False),
        corpus_root="corpora/mismatch",
        auto_create=True,
        deletion_policy="archive",
    )
    init_collection(mismatch_collection_root, mismatch_config)
    from biblicus import collections as collections_module

    original_resolve_profile = collections_module.resolve_source_profile
    collections_module.resolve_source_profile = lambda *_: SourceProfileConfig(
        name="profile",
        kind="azure-blob",
        account_name="acct",
        account_key="key",
    )
    try:
        pull_collection(mismatch_collection_root)
        raise AssertionError("Expected source profile kind mismatch to fail")
    except ValueError:
        pass
    finally:
        collections_module.resolve_source_profile = original_resolve_profile

    unsupported_collection_root = workdir / "collections" / "unsupported"
    unsupported_config = RemoteCorpusCollectionConfig.model_construct(
        schema_version=COLLECTION_SCHEMA_VERSION,
        created_at="2026-02-20T00:00:00Z",
        collection_name="unsupported",
        source=RemoteCorpusSourceConfig.model_construct(
            kind="gcs",
            profile="profile",
            name="unsupported",
            bucket=None,
            container=None,
            prefix="",
        ),
        discovery=RemoteCorpusCollectionDiscovery(mode="subfolder", depth=1, include_root_files=False),
        corpus_root="corpora/unsupported",
        auto_create=True,
        deletion_policy="archive",
    )
    original_load_collection = collections_module.load_collection_config
    collections_module.load_collection_config = lambda *_: unsupported_config
    collections_module.resolve_source_profile = lambda *_: SourceProfileConfig.model_construct(
        name="profile",
        kind="gcs",
    )
    try:
        pull_collection(unsupported_collection_root)
        raise AssertionError("Expected unsupported collection source to fail")
    except ValueError:
        pass
    finally:
        collections_module.load_collection_config = original_load_collection
        collections_module.resolve_source_profile = original_resolve_profile

    s3_collection_root = workdir / "collections" / "s3"
    s3_config = RemoteCorpusCollectionConfig(
        schema_version=COLLECTION_SCHEMA_VERSION,
        created_at="2026-02-20T00:00:00Z",
        collection_name="s3",
        source=valid_source,
        discovery=RemoteCorpusCollectionDiscovery(mode="subfolder", depth=1, include_root_files=False),
        corpus_root="corpora/s3",
        auto_create=True,
        deletion_policy="archive",
    )
    init_collection(s3_collection_root, s3_config)
    original_s3 = collections_module.S3RemoteSource
    collections_module.S3RemoteSource = lambda *_: _FakeSource([])
    collections_module.resolve_source_profile = lambda *_: SourceProfileConfig(
        name="profile",
        kind="s3",
        access_key_id="id",
        secret_access_key="secret",
    )
    try:
        pull_collection(s3_collection_root)
    finally:
        collections_module.S3RemoteSource = original_s3
        collections_module.resolve_source_profile = original_resolve_profile

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

    extractor_id, config, workers = _normalize_extraction_configuration(
        {"extractor_id": "pipeline", "configuration": None}
    )
    assert extractor_id == "pipeline", "Expected pipeline extractor id"
    assert config == {}, "Expected configuration None to normalize to empty dict"
    assert workers is None, "Expected max_workers to remain None when missing"

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
    original_retriever = pipelines_module.get_retriever
    pipelines_module.get_retriever = lambda *_: SimpleNamespace(
        build_snapshot=lambda *args, **kwargs: SimpleNamespace(snapshot_id="snap")
    )
    try:
        _run_retrieval(Corpus.open(corpus_path), retrieval_config)
    finally:
        pipelines_module.build_plan_for_index = original_build_plan
        pipelines_module.get_retriever = original_retriever

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

    class _NoopBackend:
        def run_analysis(self, *args, **kwargs):
            return None

    pipelines_module.get_analysis_backend = lambda _: _NoopBackend()
    try:
        _run_analysis(corpus_for_analysis, analysis_configs, extraction_ref)
    finally:
        pipelines_module.get_analysis_backend = original_backend

    source_corpus = Corpus.init(workdir / "cli-source", force=True)
    source_args = SimpleNamespace(
        corpus=str(source_corpus.root),
        kind="s3",
        profile="profile",
        name="demo",
        bucket="bucket",
        container=None,
        prefix="",
    )
    cmd_source_set(source_args)
    cmd_source_show(SimpleNamespace(corpus=str(source_corpus.root)))

    empty_corpus = Corpus.init(workdir / "cli-empty", force=True)
    try:
        cmd_source_show(SimpleNamespace(corpus=str(empty_corpus.root)))
        raise AssertionError("Expected source show without config to fail")
    except ValueError:
        pass

    collection_dir = workdir / "collections" / "cli-demo"
    init_collection(
        collection_dir,
        RemoteCorpusCollectionConfig(
            schema_version=COLLECTION_SCHEMA_VERSION,
            created_at="2026-02-20T00:00:00Z",
            collection_name="cli-demo",
            source=valid_source,
            discovery=RemoteCorpusCollectionDiscovery(
                mode="subfolder", depth=1, include_root_files=False
            ),
            corpus_root="corpora/cli-demo",
            auto_create=True,
            deletion_policy="archive",
        ),
    )
    cmd_collection_show(SimpleNamespace(collection=str(collection_dir)))

    recipe_dir = corpus_for_analysis.root / "recipes" / "extraction"
    recipe_dir.mkdir(parents=True, exist_ok=True)
    recipe_path = recipe_dir / "default.yml"
    recipe_path.write_text("extractor_id: pipeline\nconfiguration:\n  stages: []\n", encoding="utf-8")

    from biblicus import cli as cli_module

    manifest_path = corpus_for_analysis.extraction_snapshot_dir(
        extractor_id=extraction_ref.extractor_id, snapshot_id=extraction_ref.snapshot_id
    ) / "manifest.json"
    if not manifest_path.exists():
        manifest_path.write_text("{}", encoding="utf-8")
    resolved_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus_for_analysis, extraction_snapshot=None, analysis_label="analysis"
    )
    assert resolved_snapshot.snapshot_id == extraction_ref.snapshot_id, "Expected snapshot reuse path"

    original_loader = cli_module.load_or_build_extraction_snapshot
    cli_module.load_or_build_extraction_snapshot = lambda *args, **kwargs: SimpleNamespace(
        snapshot_id="snap-2"
    )
    try:
        manifest_path.unlink()
        resolved_fallback = _resolve_extraction_snapshot_for_analysis(
            corpus=corpus_for_analysis, extraction_snapshot=None, analysis_label="analysis"
        )
        assert resolved_fallback.snapshot_id == "snap-2", "Expected snapshot build fallback"
    finally:
        cli_module.load_or_build_extraction_snapshot = original_loader

    download_args = SimpleNamespace(
        datasets="funsd,sroie,scanned-arxiv,unknown",
        corpus_dir=str(workdir / "bench"),
        count=1,
        force=True,
    )
    import subprocess as subprocess_module

    original_run = subprocess_module.run
    subprocess_module.run = lambda *args, **kwargs: SimpleNamespace(returncode=0)
    try:
        cmd_benchmark_download(download_args)
    finally:
        subprocess_module.run = original_run

    try:
        cmd_benchmark_run(SimpleNamespace(config=str(workdir / "missing.yml"), pipelines=None, category=None, output=None))
        raise AssertionError("Expected missing benchmark config to fail")
    except FileNotFoundError:
        pass

    benchmark_config = workdir / "bench.yml"
    benchmark_config.write_text(
        "benchmark_name: demo\ncategories:\n  forms:\n    dataset: funsd\npipelines: []\n",
        encoding="utf-8",
    )
    try:
        cmd_benchmark_run(SimpleNamespace(config=str(benchmark_config), pipelines=None, category="missing", output=None))
        raise AssertionError("Expected missing benchmark category to fail")
    except ValueError:
        pass

    missing_category = CategoryConfig(
        name="missing",
        dataset="missing",
        corpus_path=workdir / "missing-corpus",
        ground_truth_subdir="gt",
        primary_metric="f1",
    )
    runner = BenchmarkRunner(
        BenchmarkConfig(
            benchmark_name="demo",
            categories={"missing": missing_category},
            pipelines=[],
            aggregate_weights={"missing": 1.0},
        )
    )
    try:
        runner.run_category(missing_category)
        raise AssertionError("Expected missing corpus in benchmark runner to fail")
    except FileNotFoundError:
        pass

    benchmark_corpus_root = workdir / "benchmark-corpus"
    benchmark_meta = benchmark_corpus_root / ".biblicus"
    benchmark_gt = benchmark_meta / "gt"
    benchmark_gt.mkdir(parents=True, exist_ok=True)
    pipeline_path = workdir / "pipeline.yml"
    pipeline_path.write_text("extractor_id: pipeline\nconfig: {}\n", encoding="utf-8")
    from biblicus.evaluation import benchmark_runner as benchmark_module

    class _FakeReport:
        avg_f1 = 0.8
        avg_recall = 0.7
        avg_precision = 0.9
        avg_word_error_rate = 0.1
        avg_lcs_ratio = 0.5
        avg_bigram_overlap = 0.6
        avg_sequence_accuracy = 0.4
        total_documents = 1

    class _FakeBenchmark:
        def __init__(self, corpus):
            self.corpus = corpus

        def evaluate_extraction(self, *args, **kwargs):
            return _FakeReport()

    class _FakeCorpus:
        def __init__(self, root):
            self.root = root
            self.meta_dir = root / ".biblicus"

        @classmethod
        def open(cls, path):
            return cls(Path(path))

        def extract(self, extractor_id, config):
            return SimpleNamespace(snapshot_id="snap-1")

    original_corpus = benchmark_module.Corpus
    original_benchmark = benchmark_module.OCRBenchmark
    benchmark_module.Corpus = _FakeCorpus
    benchmark_module.OCRBenchmark = _FakeBenchmark
    try:
        category = CategoryConfig(
            name="forms",
            dataset="funsd",
            corpus_path=benchmark_corpus_root,
            ground_truth_subdir="gt",
            primary_metric="f1",
        )
        bench_config = BenchmarkConfig(
            benchmark_name="demo",
            categories={"forms": category},
            pipelines=[pipeline_path],
            aggregate_weights={"forms": 1.0},
        )
        runner = BenchmarkRunner(bench_config)
        result = runner.run_category(category)
        assert isinstance(result, CategoryResult)
        aggregate = runner._calculate_aggregate({"forms": result})
        assert aggregate["weighted_score"] > 0
        recommendations = runner._generate_recommendations({"forms": result})
        assert recommendations.get("best_overall") == pipeline_path.stem
    finally:
        benchmark_module.Corpus = original_corpus
        benchmark_module.OCRBenchmark = original_benchmark

    graph_corpus = Corpus.init(workdir / "graph-corpus", force=True)
    try:
        cmd_graph_extract(
            SimpleNamespace(
                corpus=str(graph_corpus.root),
                configuration=None,
                override=[],
                extraction_snapshot=None,
                extractor="dependency-relations",
                configuration_name="default",
            )
        )
        raise AssertionError("Expected graph extraction without snapshot to fail")
    except ValueError:
        pass

    benchmark_status_root = workdir / "benchmark-status"
    funsd_root = benchmark_status_root / "funsd_benchmark"
    funsd_meta = funsd_root / ".biblicus"
    funsd_gt = funsd_meta / "funsd_ground_truth"
    funsd_gt.mkdir(parents=True, exist_ok=True)
    (funsd_meta / "config.json").write_text("{}", encoding="utf-8")
    (funsd_gt / "sample.txt").write_text("x", encoding="utf-8")
    cmd_benchmark_status(SimpleNamespace(corpus_dir=str(benchmark_status_root)))


@then("the pipeline recipe edge cases succeed")
def step_pipeline_recipe_edge_cases_done(context) -> None:
    assert context is not None
