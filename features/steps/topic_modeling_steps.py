from __future__ import annotations

import json
import sys
import types
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from behave import given, then, when

from features.environment import run_biblicus


@dataclass
class _FakeBerTopicBehavior:
    topic_assignments: List[int]
    topic_keywords: Dict[int, List[tuple[str, float]]]


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_json_output(standard_output: str) -> dict[str, object]:
    return json.loads(standard_output)


def _ensure_fake_bertopic_behavior(context) -> _FakeBerTopicBehavior:
    behavior = getattr(context, "fake_bertopic_behavior", None)
    if behavior is None:
        behavior = _FakeBerTopicBehavior(topic_assignments=[], topic_keywords={})
        context.fake_bertopic_behavior = behavior
    return behavior


def _install_fake_bertopic_module(context, *, use_fake_marker: bool) -> None:
    already_installed = getattr(context, "_fake_bertopic_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    if "bertopic" in sys.modules:
        original_modules["bertopic"] = sys.modules["bertopic"]

    behavior = _ensure_fake_bertopic_behavior(context)

    class BERTopic:  # noqa: N801 - external dependency uses PascalCase
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            self._kwargs = dict(kwargs)
            self._assignments: List[int] = []
            self._documents: List[str] = []

        def fit_transform(self, documents):  # type: ignore[no-untyped-def]
            self._documents = [str(doc) for doc in documents]
            assignments = list(behavior.topic_assignments)
            if not assignments:
                assignments = [0 for _ in self._documents]
            if len(assignments) < len(self._documents):
                expanded: List[int] = []
                for idx, _ in enumerate(self._documents):
                    expanded.append(assignments[idx % len(assignments)])
                assignments = expanded
            self._assignments = assignments
            return assignments, None

        def get_topic_info(self):  # type: ignore[no-untyped-def]
            counts = Counter(self._assignments)
            records = []
            for topic_id in sorted(counts.keys()):
                keywords = behavior.topic_keywords.get(topic_id, [])
                name = keywords[0][0] if keywords else f"Topic {topic_id}"
                records.append({"Topic": topic_id, "Count": counts[topic_id], "Name": name})
            return records

        def get_topic(self, topic_id: int):  # type: ignore[no-untyped-def]
            return behavior.topic_keywords.get(topic_id, [])

    bertopic_module = types.ModuleType("bertopic")
    bertopic_module.BERTopic = BERTopic
    if use_fake_marker:
        bertopic_module.__biblicus_fake__ = True

    sys.modules["bertopic"] = bertopic_module

    context._fake_bertopic_installed = True
    context._fake_bertopic_original_modules = original_modules


def _install_bertopic_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_bertopic_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    if "bertopic" in sys.modules:
        original_modules["bertopic"] = sys.modules["bertopic"]

    bertopic_module = types.ModuleType("bertopic")
    sys.modules["bertopic"] = bertopic_module

    context._fake_bertopic_unavailable_installed = True
    context._fake_bertopic_unavailable_original_modules = original_modules


def _run_reference_from_context(context) -> str:
    extractor_id = context.last_extractor_id
    run_id = context.last_extraction_run_id
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(run_id, str) and run_id
    return f"{extractor_id}:{run_id}"


@given("a fake BERTopic library is available")
def step_fake_bertopic_available(context) -> None:
    _install_fake_bertopic_module(context, use_fake_marker=True)


@given('a fake BERTopic library is available with topic assignments "{assignments}" and keywords:')
def step_fake_bertopic_with_assignments(context, assignments: str) -> None:
    _install_fake_bertopic_module(context, use_fake_marker=True)
    behavior = _ensure_fake_bertopic_behavior(context)
    parsed_assignments: List[int] = []
    for token in assignments.split(","):
        token = token.strip()
        if token:
            parsed_assignments.append(int(token))
    behavior.topic_assignments = parsed_assignments
    topic_keywords: Dict[int, List[tuple[str, float]]] = {}
    for row in context.table:
        topic_id = int(row["topic_id"].strip())
        raw_keywords = row["keywords"].strip()
        keywords = [keyword.strip() for keyword in raw_keywords.split(",") if keyword.strip()]
        scored = [(keyword, 1.0 - (index * 0.1)) for index, keyword in enumerate(keywords)]
        topic_keywords[topic_id] = scored
    behavior.topic_keywords = topic_keywords


@given("the BERTopic dependency is unavailable")
def step_bertopic_dependency_unavailable(context) -> None:
    _install_bertopic_unavailable_module(context)


def _install_fake_sklearn_module(context) -> None:
    already_installed = getattr(context, "_fake_sklearn_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    for name in [
        "sklearn",
        "sklearn.feature_extraction",
        "sklearn.feature_extraction.text",
    ]:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    class CountVectorizer:  # noqa: N801 - external dependency uses PascalCase
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            self.kwargs = dict(kwargs)

    sklearn_module = types.ModuleType("sklearn")
    feature_extraction = types.ModuleType("sklearn.feature_extraction")
    feature_text = types.ModuleType("sklearn.feature_extraction.text")
    feature_text.CountVectorizer = CountVectorizer
    feature_extraction.text = feature_text
    sklearn_module.feature_extraction = feature_extraction

    sys.modules["sklearn"] = sklearn_module
    sys.modules["sklearn.feature_extraction"] = feature_extraction
    sys.modules["sklearn.feature_extraction.text"] = feature_text

    context._fake_sklearn_installed = True
    context._fake_sklearn_original_modules = original_modules


def _install_sklearn_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_sklearn_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    for name in [
        "sklearn",
        "sklearn.feature_extraction",
        "sklearn.feature_extraction.text",
    ]:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]
            sys.modules.pop(name, None)

    sklearn_module = types.ModuleType("sklearn")
    sys.modules["sklearn"] = sklearn_module

    context._fake_sklearn_unavailable_installed = True
    context._fake_sklearn_unavailable_original_modules = original_modules


@given("a fake BERTopic library without a fake marker is available")
def step_fake_bertopic_without_marker(context) -> None:
    _install_fake_bertopic_module(context, use_fake_marker=False)
    _install_fake_sklearn_module(context)


@given("the scikit-learn dependency is unavailable")
def step_sklearn_dependency_unavailable(context) -> None:
    _install_sklearn_unavailable_module(context)


@when('I run a topic analysis in corpus "{corpus_name}" using recipe "{recipe_file}" and the latest extraction run')
def step_run_topic_analysis_with_latest_extraction(context, corpus_name: str, recipe_file: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    recipe_path = Path(workdir) / recipe_file
    run_ref = _run_reference_from_context(context)
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "topics",
        "--recipe",
        str(recipe_path),
        "--extraction-run",
        run_ref,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@when('I run a topic analysis in corpus "{corpus_name}" using recipe "{recipe_file}"')
def step_run_topic_analysis_with_recipe(context, corpus_name: str, recipe_file: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    recipe_path = Path(workdir) / recipe_file
    args = ["--corpus", str(corpus), "analyze", "topics", "--recipe", str(recipe_path)]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@then("the topic analysis output includes {count:d} topics")
def step_topic_analysis_output_includes_topic_count(context, count: int) -> None:
    output = context.last_analysis_output
    topics = output["report"]["topics"]
    assert len(topics) == count


@then("the topic analysis output includes topic labels:")
def step_topic_analysis_output_includes_labels(context) -> None:
    output = context.last_analysis_output
    topics = output["report"]["topics"]
    labels = {topic["label"] for topic in topics}
    expected = {row["label"].strip() for row in context.table}
    assert labels == expected


@then('the topic analysis output includes topic label "{label}"')
def step_topic_analysis_output_includes_label(context, label: str) -> None:
    output = context.last_analysis_output
    topics = output["report"]["topics"]
    labels = {topic["label"] for topic in topics}
    assert label in labels


@then("the BERTopic analysis report includes ngram range {min_value:d} and {max_value:d}")
def step_bertopic_report_includes_ngram_range(context, min_value: int, max_value: int) -> None:
    output = context.last_analysis_output
    report = output["report"]["bertopic_analysis"]
    vectorizer = report.get("vectorizer")
    assert isinstance(vectorizer, dict)
    ngram_range = vectorizer.get("ngram_range")
    assert ngram_range == [min_value, max_value]


@then('the BERTopic analysis report includes stop words "{stop_words}"')
def step_bertopic_report_includes_stop_words(context, stop_words: str) -> None:
    output = context.last_analysis_output
    report = output["report"]["bertopic_analysis"]
    vectorizer = report.get("vectorizer")
    assert isinstance(vectorizer, dict)
    value = vectorizer.get("stop_words")
    assert value == stop_words


@then('the topic analysis output label source is "{source}"')
def step_topic_analysis_output_label_source(context, source: str) -> None:
    output = context.last_analysis_output
    topics = output["report"]["topics"]
    assert topics
    sources = {topic["label_source"] for topic in topics}
    assert sources == {source}


@then("the topic analysis output llm extraction output documents equals {count:d}")
def step_topic_analysis_output_llm_documents(context, count: int) -> None:
    if not hasattr(context, "last_analysis_output"):
        result = getattr(context, "last_result", None)
        stderr = getattr(result, "stderr", "") if result is not None else ""
        raise AssertionError(f"Topic analysis output missing. stderr: {stderr}")
    output = context.last_analysis_output
    report = output["report"]["llm_extraction"]
    assert report is not None
    assert report["output_documents"] == count


@then("the topic analysis output uses the latest extraction run reference")
def step_topic_analysis_output_uses_latest_extraction(context) -> None:
    output = context.last_analysis_output
    run_input = output["run"]["input"]
    extraction_run = run_input["extraction_run"]
    assert extraction_run["extractor_id"] == context.last_extractor_id
    assert extraction_run["run_id"] == context.last_extraction_run_id
