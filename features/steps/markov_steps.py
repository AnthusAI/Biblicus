from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from behave import given, then, when

from features.environment import run_biblicus


@dataclass
class _FakeHmmlearnBehavior:
    predicted_states: List[int]
    include_transmat: bool = True
    include_startprob: bool = True
    startprob_values: Optional[List[float]] = None


def _ensure_fake_hmmlearn_behavior(context) -> _FakeHmmlearnBehavior:
    behavior = getattr(context, "fake_hmmlearn_behavior", None)
    if behavior is None:
        behavior = _FakeHmmlearnBehavior(predicted_states=[])
        context.fake_hmmlearn_behavior = behavior
    return behavior


def _install_fake_hmmlearn_module(context) -> None:
    already_installed = getattr(context, "_fake_hmmlearn_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    for name in ["hmmlearn", "hmmlearn.hmm"]:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    behavior = _ensure_fake_hmmlearn_behavior(context)

    class GaussianHMM:  # noqa: N801 - external dependency uses PascalCase
        def __init__(self, n_components: int, **kwargs):  # type: ignore[no-untyped-def]
            self.n_components = int(n_components)
            if behavior.include_startprob:
                if behavior.startprob_values:
                    values = list(behavior.startprob_values)
                    if len(values) < self.n_components:
                        values.extend([0.0 for _ in range(self.n_components - len(values))])
                    self.startprob_ = values[: self.n_components]
                else:
                    self.startprob_ = [0.0 for _ in range(self.n_components)]
            if behavior.include_transmat:
                self.transmat_ = [
                    [0.0 for _ in range(self.n_components)] for _ in range(self.n_components)
                ]

        def fit(self, X, lengths=None):  # type: ignore[no-untyped-def]
            sequence = list(behavior.predicted_states or [])
            if not sequence:
                sequence = [0 for _ in range(len(X))]
            if len(sequence) < len(X):
                expanded: List[int] = []
                for idx in range(len(X)):
                    expanded.append(sequence[idx % len(sequence)])
                sequence = expanded
            counts: Dict[tuple[int, int], int] = {}
            totals: Dict[int, int] = {}
            for prev, nxt in zip(sequence, sequence[1:]):
                counts[(prev, nxt)] = counts.get((prev, nxt), 0) + 1
                totals[prev] = totals.get(prev, 0) + 1
            if behavior.include_transmat:
                for from_state in range(self.n_components):
                    denom = totals.get(from_state, 0) or 1
                    for to_state in range(self.n_components):
                        count = counts.get((from_state, to_state), 0)
                        self.transmat_[from_state][to_state] = float(count) / float(denom)
            return self

        def predict(self, X, lengths=None):  # type: ignore[no-untyped-def]
            sequence = list(behavior.predicted_states or [])
            if not sequence:
                sequence = [0 for _ in range(len(X))]
            if len(sequence) < len(X):
                expanded: List[int] = []
                for idx in range(len(X)):
                    expanded.append(sequence[idx % len(sequence)])
                sequence = expanded
            return sequence[: len(X)]

    class CategoricalHMM(GaussianHMM):  # noqa: N801 - external dependency uses PascalCase
        pass

    hmm_module = types.ModuleType("hmmlearn.hmm")
    hmm_module.GaussianHMM = GaussianHMM
    hmm_module.CategoricalHMM = CategoricalHMM

    root = types.ModuleType("hmmlearn")
    root.hmm = hmm_module

    sys.modules["hmmlearn"] = root
    sys.modules["hmmlearn.hmm"] = hmm_module

    context._fake_hmmlearn_installed = True
    context._fake_hmmlearn_original_modules = original_modules


def _install_hmmlearn_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_hmmlearn_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    for name in ["hmmlearn", "hmmlearn.hmm"]:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    sys.modules["hmmlearn"] = types.ModuleType("hmmlearn")
    sys.modules.pop("hmmlearn.hmm", None)

    context._fake_hmmlearn_unavailable_installed = True
    context._fake_hmmlearn_unavailable_original_modules = original_modules


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_json_output(standard_output: str) -> dict[str, object]:
    return json.loads(standard_output)


def _load_markov_segments(context, corpus_name: str = "corpus") -> List[dict[str, object]]:
    output = context.last_analysis_output
    run_id = output["run"]["run_id"]
    corpus = _corpus_path(context, corpus_name)
    path = corpus / ".biblicus" / "runs" / "analysis" / "markov" / run_id / "segments.jsonl"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def _latest_extraction_run_manifest_path(context, corpus_name: str) -> Path:
    corpus = _corpus_path(context, corpus_name)
    extractor_id = context.last_extractor_id
    run_id = context.last_extraction_run_id
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(run_id, str) and run_id
    return corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id / "manifest.json"


def _latest_extraction_run_root(context, corpus_name: str) -> Path:
    return _latest_extraction_run_manifest_path(context, corpus_name).parent


def _run_reference_from_context(context) -> str:
    extractor_id = context.last_extractor_id
    run_id = context.last_extraction_run_id
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(run_id, str) and run_id
    return f"{extractor_id}:{run_id}"


@given('a fake hmmlearn library is available with predicted states "{states}"')
def step_fake_hmmlearn_available(context, states: str) -> None:
    _install_fake_hmmlearn_module(context)
    behavior = _ensure_fake_hmmlearn_behavior(context)
    parsed: List[int] = []
    for token in (states or "").split(","):
        token = token.strip()
        if not token:
            continue
        parsed.append(int(token))
    behavior.predicted_states = parsed
    behavior.include_startprob = True
    behavior.startprob_values = None


@given("a fake hmmlearn library is available without transmat_ output")
def step_fake_hmmlearn_without_transmat(context) -> None:
    _install_fake_hmmlearn_module(context)
    behavior = _ensure_fake_hmmlearn_behavior(context)
    behavior.include_transmat = False


@given('a fake hmmlearn library is available with start probabilities "{values}"')
def step_fake_hmmlearn_with_startprob(context, values: str) -> None:
    _install_fake_hmmlearn_module(context)
    behavior = _ensure_fake_hmmlearn_behavior(context)
    parsed: List[float] = []
    for token in (values or "").split(","):
        token = token.strip()
        if not token:
            continue
        parsed.append(float(token))
    behavior.startprob_values = parsed
    behavior.include_startprob = True


@given("a fake hmmlearn library is available without start probabilities")
def step_fake_hmmlearn_without_startprob(context) -> None:
    _install_fake_hmmlearn_module(context)
    behavior = _ensure_fake_hmmlearn_behavior(context)
    behavior.include_startprob = False


@given("the hmmlearn dependency is unavailable")
def step_hmmlearn_dependency_unavailable(context) -> None:
    _install_hmmlearn_unavailable_module(context)


@when(
    'I run a markov analysis in corpus "{corpus_name}" using recipe "{recipe_file}" and the latest extraction run'
)
def step_run_markov_analysis_with_latest_extraction(
    context, corpus_name: str, recipe_file: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    recipe_path = Path(workdir) / recipe_file
    run_ref = _run_reference_from_context(context)
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "markov",
        "--recipe",
        str(recipe_path),
        "--extraction-run",
        run_ref,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode != 0:
        raise AssertionError(f"Markov analysis failed. stderr: {result.stderr}")
    context.last_analysis_output = _parse_json_output(result.stdout)


@when(
    'I attempt to run a markov analysis in corpus "{corpus_name}" using recipe "{recipe_file}" '
    "and the latest extraction run"
)
def step_attempt_run_markov_analysis_with_latest_extraction(
    context, corpus_name: str, recipe_file: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    recipe_path = Path(workdir) / recipe_file
    run_ref = _run_reference_from_context(context)
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "markov",
        "--recipe",
        str(recipe_path),
        "--extraction-run",
        run_ref,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@when('I run a markov analysis in corpus "{corpus_name}" using recipe "{recipe_file}"')
def step_run_markov_analysis_without_extraction_run(
    context, corpus_name: str, recipe_file: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    recipe_path = Path(workdir) / recipe_file
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "markov",
        "--recipe",
        str(recipe_path),
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@then("the markov analysis output includes {count:d} states")
def step_markov_output_includes_state_count(context, count: int) -> None:
    output = context.last_analysis_output
    states = output["report"]["states"]
    assert len(states) == count


@then(
    "the markov analysis output includes a transition from state {from_state:d} to state {to_state:d}"
)
def step_markov_output_includes_transition(context, from_state: int, to_state: int) -> None:
    output = context.last_analysis_output
    transitions = output["report"]["transitions"]
    edges = {(edge["from_state"], edge["to_state"]) for edge in transitions}
    assert (from_state, to_state) in edges


@then("the markov analysis output includes {count:d} decoded item path")
def step_markov_output_includes_decoded_path_count(context, count: int) -> None:
    output = context.last_analysis_output
    paths = output["report"]["decoded_paths"]
    assert len(paths) == count


@then("the analysis run includes a graphviz transitions file")
def step_markov_run_includes_graphviz_file(context) -> None:
    output = context.last_analysis_output
    run_id = output["run"]["run_id"]
    corpus = _corpus_path(context, "corpus")
    path = corpus / ".biblicus" / "runs" / "analysis" / "markov" / run_id / "transitions.dot"
    assert path.is_file()


@then("the markov analysis run includes more than 1 segment")
def step_markov_run_includes_more_than_one_segment(context) -> None:
    segments = _load_markov_segments(context)
    assert len(segments) > 1


@then("the markov analysis run includes a segment with text:")
def step_markov_run_includes_segment_text(context) -> None:
    expected = str(getattr(context, "text", "") or "").strip()
    segments = _load_markov_segments(context)
    assert any(str(segment.get("text", "")).strip() == expected for segment in segments)


@then("the markov analysis run includes an observations file")
def step_markov_run_includes_observations_file(context) -> None:
    output = context.last_analysis_output
    run_id = output["run"]["run_id"]
    corpus = _corpus_path(context, "corpus")
    path = corpus / ".biblicus" / "runs" / "analysis" / "markov" / run_id / "observations.jsonl"
    assert path.is_file()


@given("I append a non-extracted item to the latest extraction run manifest")
@when("I append a non-extracted item to the latest extraction run manifest")
def step_append_non_extracted_item_to_manifest(context) -> None:
    manifest_path = _latest_extraction_run_manifest_path(context, "corpus")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    assert isinstance(items, list)
    items.append(
        {
            "item_id": "item-non-extracted",
            "status": "failed",
            "final_text_relpath": None,
            "error_type": "failed",
            "error_message": "failed",
            "step_results": [],
        }
    )
    payload["items"] = items
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@given("I blank the extracted text for the 4th ingested item in the latest extraction run")
@when("I blank the extracted text for the 4th ingested item in the latest extraction run")
def step_blank_extracted_text_for_fourth_item(context) -> None:
    ingested_ids = getattr(context, "ingested_ids", None)
    assert isinstance(ingested_ids, list)
    assert len(ingested_ids) >= 4
    target_id = str(ingested_ids[3])

    manifest_path = _latest_extraction_run_manifest_path(context, "corpus")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    assert isinstance(items, list)
    target_item = None
    for item in items:
        if isinstance(item, dict) and item.get("item_id") == target_id:
            target_item = item
            break
    assert target_item is not None
    relpath = target_item.get("final_text_relpath")
    assert isinstance(relpath, str) and relpath
    text_path = _latest_extraction_run_root(context, "corpus") / relpath
    text_path.write_text("", encoding="utf-8")


@then("the markov analysis text collection report includes:")
def step_markov_text_collection_report_includes(context) -> None:
    output = context.last_analysis_output
    report = output["report"]["text_collection"]
    for row in context.table:
        field = str(row["field"])
        expected = int(row["value"])
        assert int(report[field]) == expected


@then('the markov analysis text collection report warnings include "{snippet}"')
def step_markov_text_collection_report_warnings_include(context, snippet: str) -> None:
    output = context.last_analysis_output
    report = output["report"]["text_collection"]
    warnings = report.get("warnings", [])
    assert isinstance(warnings, list)
    combined = "\n".join(str(value) for value in warnings)
    assert snippet in combined


@then("every Markov state report has 0 exemplars")
def step_every_markov_state_report_has_zero_exemplars(context) -> None:
    output = context.last_analysis_output
    states = output["report"]["states"]
    for state in states:
        assert isinstance(state, dict)
        exemplars = state.get("exemplars", [])
        assert isinstance(exemplars, list)
        assert len(exemplars) == 0


@then("the graphviz transitions file contains no edges")
def step_graphviz_transitions_file_contains_no_edges(context) -> None:
    output = context.last_analysis_output
    run_id = output["run"]["run_id"]
    corpus = _corpus_path(context, "corpus")
    path = corpus / ".biblicus" / "runs" / "analysis" / "markov" / run_id / "transitions.dot"
    contents = path.read_text(encoding="utf-8")
    assert "->" not in contents
