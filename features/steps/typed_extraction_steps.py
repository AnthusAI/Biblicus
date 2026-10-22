from __future__ import annotations

import json
import shlex
import sys
import types
from pathlib import Path
from typing import Any, Dict, List

from behave import given, then, when
from pydantic import ValidationError

from biblicus.corpus import Corpus
from biblicus.typed_extraction import EntitySpan, TypedEntity, normalise_alias
from features.environment import run_biblicus
from features.steps.cli_steps import _resolve_fixture_path

NO_KEY = "-"


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


class _FakeGliner2State:
    def __init__(self) -> None:
        self.entities: List[Dict[str, Any]] = []
        self.relations: List[Dict[str, Any]] = []
        self.windows: List[str] = []
        self.loads: List[Dict[str, Any]] = []


def _fake_state(context) -> _FakeGliner2State:
    state = getattr(context, "fake_gliner2_state", None)
    if state is None:
        state = _FakeGliner2State()
        context.fake_gliner2_state = state
    return state


def _occurrences(window: str, phrase: str) -> List[int]:
    starts = []
    cursor = window.find(phrase)
    while cursor != -1:
        starts.append(cursor)
        cursor = window.find(phrase, cursor + 1)
    return starts


def _install_fake_gliner2(context) -> None:
    if getattr(context, "fake_gliner2_installed", False):
        return
    state = _fake_state(context)
    original = sys.modules.get("gliner2")

    class GLiNER2:  # noqa: N801 - external dependency uses this name
        @classmethod
        def from_pretrained(cls, model_id, **kwargs):  # type: ignore[no-untyped-def]
            state.loads.append({"model_id": model_id, **kwargs})
            return cls()

        def extract_entities(  # type: ignore[no-untyped-def]
            self, window, labels, threshold=0.5, include_spans=False, include_confidence=False
        ):
            state.windows.append(window)
            found: Dict[str, List[Dict[str, Any]]] = {}
            for row in state.entities:
                if row["label"] not in labels or row["score"] < threshold:
                    continue
                for start in _occurrences(window, row["text"]):
                    found.setdefault(row["label"], []).append(
                        {
                            "text": row["text"],
                            "start": start,
                            "end": start + len(row["text"]),
                            "confidence": row["score"],
                        }
                    )
            return {"entities": found}

        def extract_relations(  # type: ignore[no-untyped-def]
            self, window, labels, threshold=0.5, include_spans=False, include_confidence=False
        ):
            found: Dict[str, List[Dict[str, Any]]] = {}
            for row in state.relations:
                if row["label"] not in labels or row["score"] < threshold:
                    continue
                heads = _occurrences(window, row["subject"])
                tails = _occurrences(window, row["object"])
                if not heads or not tails:
                    continue
                found.setdefault(row["label"], []).append(
                    {
                        "head": {
                            "text": row["subject"],
                            "start": heads[0],
                            "end": heads[0] + len(row["subject"]),
                            "confidence": row["score"],
                        },
                        "tail": {
                            "text": row["object"],
                            "start": tails[0],
                            "end": tails[0] + len(row["object"]),
                            "confidence": row["score"],
                        },
                    }
                )
            return {"relation_extraction": found}

    module = types.ModuleType("gliner2")
    module.GLiNER2 = GLiNER2
    sys.modules["gliner2"] = module
    context.fake_gliner2_installed = True

    def restore() -> None:
        if original is None:
            sys.modules.pop("gliner2", None)
        else:
            sys.modules["gliner2"] = original

    context.add_cleanup(restore)


@given("a fake GLiNER2 library finds these entities:")
def step_fake_gliner2_entities(context) -> None:
    _install_fake_gliner2(context)
    state = _fake_state(context)
    state.entities = [
        {"text": row["text"], "label": row["label"], "score": float(row["score"])}
        for row in context.table
    ]


@given("a fake GLiNER2 library finds these relations:")
def step_fake_gliner2_relations(context) -> None:
    _install_fake_gliner2(context)
    state = _fake_state(context)
    state.relations = [
        {
            "subject": row["subject"],
            "label": row["label"],
            "object": row["object"],
            "score": float(row["score"]),
        }
        for row in context.table
    ]


@given("the GLiNER2 dependency is not installed")
@when("the GLiNER2 dependency is not installed")
def step_gliner2_not_installed(context) -> None:
    original = sys.modules.get("gliner2")
    sys.modules["gliner2"] = None

    def restore() -> None:
        if original is None:
            sys.modules.pop("gliner2", None)
        else:
            sys.modules["gliner2"] = original

    context.add_cleanup(restore)


def _item_ids(context) -> Dict[str, str]:
    if not hasattr(context, "typed_item_ids"):
        context.typed_item_ids = {}
    return context.typed_item_ids


@given('the corpus "{corpus_name}" has an item "{name}" with text:')
def step_corpus_item_with_text(context, corpus_name: str, name: str) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    _item_ids(context)[name] = corpus.ingest_note(context.text, title=name).item_id


@given('the corpus "{corpus_name}" has an item "{name}" with escaped text "{text}"')
def step_corpus_item_escaped_text(context, corpus_name: str, name: str, text: str) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    decoded = text.encode("utf-8").decode("unicode_escape")
    _item_ids(context)[name] = corpus.ingest_note(decoded, title=name).item_id


@given('the corpus "{corpus_name}" has an item "{name}" of {count:d} paragraphs of {words:d} words')
def step_corpus_item_paragraphs(
    context, corpus_name: str, name: str, count: int, words: int
) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    paragraph = " ".join(["filler"] * words)
    text = "\n\n".join(f"{paragraph} Guard {index}" for index in range(count))
    _item_ids(context)[name] = corpus.ingest_note(text, title=name).item_id


@given(
    'the corpus "{corpus_name}" has an item "{name}" of one unbroken run of {count:d} characters'
)
def step_corpus_item_unbroken(context, corpus_name: str, name: str, count: int) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    _item_ids(context)[name] = corpus.ingest_note("x" * count, title=name).item_id


@given('I built a pass-through extraction snapshot in corpus "{corpus_name}"')
@when('I build a pass-through extraction snapshot in corpus "{corpus_name}"')
def step_build_pass_through_snapshot(context, corpus_name: str) -> None:
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(_corpus_path(context, corpus_name)),
            "extract",
            "build",
            "--stage",
            "pass-through-text",
        ],
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    context.typed_snapshot_reference = f"pipeline:{manifest['snapshot_id']}"


def _expand(context, options: str) -> List[str]:
    expanded: List[str] = []
    for token in shlex.split(options):
        if expanded and expanded[-1] in ("--vocabulary", "--registry"):
            token = str(_resolve_fixture_path(context, token))
        elif expanded and expanded[-1] == "--out":
            token = str(context.workdir / token)
        elif token.startswith("item:"):
            token = _item_ids(context)[token[len("item:") :]]
        elif token == "snapshot:latest":
            token = context.typed_snapshot_reference
        expanded.append(token)
    return expanded


def _run_typed_entities(context, corpus_name: str, options: str) -> None:
    arguments = [
        "--corpus",
        str(_corpus_path(context, corpus_name)),
        "extract",
        "typed-entities",
    ] + _expand(context, options)
    context.last_result = run_biblicus(context, arguments)
    if not hasattr(context, "typed_stdout"):
        context.typed_stdout = []
    context.typed_stdout.append(context.last_result.stdout)
    if context.last_result.returncode == 0:
        context.typed_output = json.loads(context.last_result.stdout)


@when('I extract typed entities in corpus "{corpus_name}" with options "{options}"')
def step_extract_typed_entities(context, corpus_name: str, options: str) -> None:
    _run_typed_entities(context, corpus_name, options)


@when('I extract typed entities in corpus "{corpus_name}" with options "{options}" a second time')
def step_extract_typed_entities_again(context, corpus_name: str, options: str) -> None:
    _run_typed_entities(context, corpus_name, options)


def _item_result(context, name: str) -> Dict[str, Any]:
    item_id = _item_ids(context)[name]
    matches = [item for item in context.typed_output["items"] if item["item_id"] == item_id]
    assert len(matches) == 1, f"item {name} missing from output"
    return matches[0]


def _item_text(context, corpus_name: str, name: str) -> str:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    reference = context.typed_snapshot_reference.split(":", 1)
    text = corpus.read_extracted_text(
        extractor_id=reference[0], snapshot_id=reference[1], item_id=_item_ids(context)[name]
    )
    assert text is not None
    return text


@then('item "{name}" has these entities:')
def step_item_entities(context, name: str) -> None:
    actual = [
        (
            entity["text"],
            entity["kind"],
            entity["state"],
            entity["entity_key"] if entity["entity_key"] is not None else NO_KEY,
        )
        for entity in _item_result(context, name)["entities"]
    ]
    expected = [
        (row["text"], row["kind"], row["state"], row["entity_key"]) for row in context.table
    ]
    assert actual == expected, actual


@then('item "{name}" has these relations:')
def step_item_relations(context, name: str) -> None:
    item = _item_result(context, name)
    texts = {entity["id"]: entity["text"] for entity in item["entities"]}
    actual = [
        (relation["type"], texts[relation["subject"]], texts[relation["object"]], relation["state"])
        for relation in item["relations"]
    ]
    expected = [(row["type"], row["subject"], row["object"], row["state"]) for row in context.table]
    assert actual == expected, actual


@then('item "{name}" has no relations')
def step_item_no_relations(context, name: str) -> None:
    item = _item_result(context, name)
    assert item["relations"] == [], item


@then('item "{name}" has no entities and no relations')
def step_item_empty(context, name: str) -> None:
    item = _item_result(context, name)
    assert item["entities"] == [] and item["relations"] == [], item


@then(
    'every entity and relation of item "{name}" in corpus "{corpus_name}" carries its item id and offsets into the text'
)
def step_evidence(context, name: str, corpus_name: str) -> None:
    item = _item_result(context, name)
    text = _item_text(context, corpus_name, name)
    assert item["item_id"] == _item_ids(context)[name]
    assert item["entities"], "scenario needs at least one entity"
    for entity in item["entities"]:
        span = entity["span"]
        assert text[span["start"] : span["end"]] == entity["text"], entity
    by_id = {entity["id"]: entity for entity in item["entities"]}
    for relation in item["relations"]:
        span = relation["span"]
        for endpoint in (by_id[relation["subject"]], by_id[relation["object"]]):
            assert span["start"] <= endpoint["span"]["start"], relation
            assert endpoint["span"]["end"] <= span["end"], relation


@then("every entity kind and relation type in the output belongs to the vocabulary")
def step_vocabulary_closed(context) -> None:
    kinds = {"maker", "model", "licence"}
    types_allowed = {"made_by", "licensed_under"}
    for item in context.typed_output["items"]:
        assert {entity["kind"] for entity in item["entities"]} <= kinds
        assert {relation["type"] for relation in item["relations"]} <= types_allowed


@then(
    "the output summary counts {items:d} items, {entities:d} entities, {resolved:d} resolved, {proposed:d} proposed and {relations:d} relations"
)
def step_summary(
    context, items: int, entities: int, resolved: int, proposed: int, relations: int
) -> None:
    assert context.typed_output["summary"] == {
        "items": items,
        "entities": entities,
        "resolved": resolved,
        "proposed": proposed,
        "relations": relations,
    }, context.typed_output["summary"]


@then(
    'the output names backend "{backend_id}" with threshold {threshold:f} and vocabulary "{publication}" version {version:d}'
)
def step_backend_identity(
    context, backend_id: str, threshold: float, publication: str, version: int
) -> None:
    output = context.typed_output
    assert output["backend"]["id"] == backend_id
    assert output["backend"]["threshold"] == threshold
    assert output["vocabulary"]["publication"] == publication
    assert output["vocabulary"]["version"] == version
    assert len(output["vocabulary"]["hash"]) == 64
    assert output["schema_version"] == 1


@then('the output names model "{model}" at revision "{revision}"')
def step_model_identity(context, model: str, revision: str) -> None:
    assert context.typed_output["backend"]["model"] == model
    assert context.typed_output["backend"]["revision"] == revision


@then("the output names no model and no revision")
def step_no_model(context) -> None:
    assert context.typed_output["backend"]["model"] is None
    assert context.typed_output["backend"]["revision"] is None


@then("the output contains no timestamps")
def step_no_timestamps(context) -> None:
    text = context.last_result.stdout
    for forbidden in ("created_at", "generated_at", "timestamp", "elapsed"):
        assert forbidden not in text, forbidden


@then("both runs print identical standard output")
def step_identical_stdout(context) -> None:
    first, second = context.typed_stdout[-2:]
    assert first and first == second


def _run_directories(context, corpus_name: str) -> List[Path]:
    root = _corpus_path(context, corpus_name) / "analysis" / "typed-entities"
    return sorted(path for path in root.iterdir() if path.is_dir() and path.name != "cache")


@then('the corpus "{corpus_name}" stores the output under its typed-entities analysis folder')
def step_stored_output(context, corpus_name: str) -> None:
    directories = _run_directories(context, corpus_name)
    assert len(directories) == 1, directories
    stored = (directories[0] / "output.json").read_text(encoding="utf-8")
    assert stored == context.last_result.stdout


@then(
    'the run metadata of corpus "{corpus_name}" reports {calls:d} backend calls and {hits:d} cache hits'
)
def step_metadata_counts(context, corpus_name: str, calls: int, hits: int) -> None:
    metadata = max(
        (
            json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
            for directory in _run_directories(context, corpus_name)
        ),
        key=lambda candidate: candidate["created_at"],
    )
    assert metadata["backend_calls"] == calls, metadata
    assert metadata["cache_hits"] == hits, metadata
    assert metadata["created_at"]
    assert metadata["output_path"].endswith(f"{metadata['run_id']}/output.json")


@then('the corpus "{corpus_name}" has {count:d} typed-entities runs')
def step_run_count(context, corpus_name: str, count: int) -> None:
    assert len(_run_directories(context, corpus_name)) == count


@then('the file "{filename}" matches the standard output')
def step_file_matches_stdout(context, filename: str) -> None:
    path = (context.workdir / filename).resolve()
    assert path.read_text(encoding="utf-8") == context.last_result.stdout


@then("the fake GLiNER2 library loaded model {model_id} at revision {revision} {count:d} time")
@then("the fake GLiNER2 library loaded model {model_id} at revision {revision} {count:d} times")
def step_fake_loaded(context, model_id: str, revision: str, count: int) -> None:
    loads = _fake_state(context).loads
    assert loads == [{"model_id": model_id, "revision": revision}] * count, loads


@then("the fake GLiNER2 library read {count:d} windows")
def step_fake_windows(context, count: int) -> None:
    assert len(_fake_state(context).windows) == count, len(_fake_state(context).windows)


@then("the fake GLiNER2 library read no windows")
def step_fake_no_windows(context) -> None:
    assert _fake_state(context).windows == []


@then("no fake GLiNER2 window is longer than {limit:d} characters")
def step_window_limit(context, limit: int) -> None:
    assert all(len(window) <= limit for window in _fake_state(context).windows)


@then(
    'every entity text in the output appears at its offsets in item "{name}" of corpus "{corpus_name}"'
)
def step_offsets_global(context, name: str, corpus_name: str) -> None:
    text = _item_text(context, corpus_name, name)
    for entity in _item_result(context, name)["entities"]:
        assert text[entity["span"]["start"] : entity["span"]["end"]] == entity["text"]


@then("normalising {first} and {second} gives the same alias")
def step_normalise_equal(context, first: str, second: str) -> None:
    assert normalise_alias(first.strip('"')) == normalise_alias(second.strip('"'))


@then("an entity that is resolved without an entity key is rejected")
def step_resolved_without_key(context) -> None:
    try:
        TypedEntity(
            id="e1",
            kind="maker",
            text="name-a",
            state="resolved",
            entity_key=None,
            span=EntitySpan(start=0, end=6),
            score=1.0,
        )
    except ValidationError as error:
        assert "entity_key is set exactly when state is resolved" in str(error)
        return
    raise AssertionError("expected a validation error")


@then("a span that ends before it starts is rejected")
def step_span_order(context) -> None:
    try:
        EntitySpan(start=5, end=5)
    except ValidationError as error:
        assert "span end must be greater than start" in str(error)
        return
    raise AssertionError("expected a validation error")


@given("the pinned GLiNER2 model is cached locally")
def step_pinned_model_cached(context) -> None:
    import importlib.util
    import os

    from huggingface_hub import constants, try_to_load_from_cache

    from biblicus.typed_extraction_backends import GLINER2_MODEL, GLINER2_REVISION

    if importlib.util.find_spec("gliner2") is None:
        context.scenario.skip("The typed-extraction extra is not installed.")
        return
    home = Path(getattr(context, "_prior_home", None) or Path.home())
    cache_directory = str(Path(os.environ.get("HF_HOME", home / ".cache" / "huggingface")) / "hub")
    cached = try_to_load_from_cache(
        GLINER2_MODEL, "config.json", revision=GLINER2_REVISION, cache_dir=cache_directory
    )
    if not isinstance(cached, str):
        context.scenario.skip("The pinned GLiNER2 checkpoint is not in the local cache.")
        return
    previous = (constants.HF_HUB_CACHE, constants.HF_HUB_OFFLINE)
    constants.HF_HUB_CACHE = cache_directory
    constants.HF_HUB_OFFLINE = True

    def restore() -> None:
        constants.HF_HUB_CACHE, constants.HF_HUB_OFFLINE = previous

    context.add_cleanup(restore)


@then("the output has at least {count:d} entities")
def step_output_has_entities(context, count: int) -> None:
    assert context.typed_output["summary"]["entities"] >= count, context.typed_output["summary"]
