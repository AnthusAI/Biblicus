"""
Generate a Markdown report for a Markov analysis snapshot.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def _load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _load_catalog_items(corpus_path: Path) -> Dict[str, Dict[str, object]]:
    catalog_path = corpus_path / "metadata" / "catalog.json"
    if not catalog_path.exists():
        catalog_path = corpus_path / ".biblicus" / "catalog.json"
    catalog = _load_json(catalog_path)
    catalog_items = catalog["items"]
    if not isinstance(catalog_items, dict):
        raise ValueError("Expected catalog.items to be a mapping")
    return catalog_items


def _align_segments_to_states(
    *, segments: List[Dict[str, object]], decoded_paths: Dict[str, List[int]]
) -> List[Tuple[int, Dict[str, object]]]:
    aligned: List[Tuple[int, Dict[str, object]]] = []
    by_item: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for segment in segments:
        item_id = str(segment.get("item_id") or "")
        if not item_id:
            continue
        by_item[item_id].append(segment)
    for item_id, item_segments in by_item.items():
        state_sequence = decoded_paths.get(item_id)
        if state_sequence is None:
            continue
        ordered_segments = sorted(
            item_segments, key=lambda entry: int(entry.get("segment_index") or 0)
        )
        for segment, state_id in zip(ordered_segments, state_sequence):
            aligned.append((int(state_id), segment))
    return aligned


def _segments_by_state(
    aligned: List[Tuple[int, Dict[str, object]]],
) -> Dict[int, List[Dict[str, object]]]:
    grouped: Dict[int, List[Dict[str, object]]] = defaultdict(list)
    for state_id, segment in aligned:
        grouped[state_id].append(segment)
    return grouped


def _state_label(state: Dict[str, object]) -> str:
    raw_label = str(state.get("label") or "").strip()
    if raw_label:
        return raw_label
    return f"State {int(state.get('state_id') or 0)}"


def _state_heading(state: Dict[str, object]) -> str:
    return f"{_state_label(state)} (State {int(state.get('state_id') or 0)})"


def _state_label_map(states: Iterable[Dict[str, object]]) -> Dict[int, str]:
    labels: Dict[int, str] = {}
    for state in states:
        state_id = int(state.get("state_id") or 0)
        labels[state_id] = _state_label(state)
    return labels


def _observation_description(config: Dict[str, object]) -> str:
    segmentation = dict(config.get("segmentation") or {})
    observations = dict(config.get("observations") or {})
    model = dict(config.get("model") or {})
    topic_modeling = dict(config.get("topic_modeling") or {})

    segmentation_method = str(segmentation.get("method") or "unknown")
    family = str(model.get("family") or "unknown")
    if family == "categorical":
        source = str(observations.get("categorical_source") or "unknown")
        description = f"Categorical HMM over `{source}` observations"
    else:
        encoder = str(observations.get("encoder") or "unknown")
        text_source = str(observations.get("text_source") or "segment_text")
        description = f"{family.title()} HMM over `{encoder}` features from `{text_source}`"
    if bool(topic_modeling.get("enabled")):
        description += " with segment topic modeling enabled"
    return f"`{segmentation_method}` segmentation feeding {description}"


def _artifact_line(run_dir: Path, name: str) -> str:
    artifact_path = run_dir / name
    status = "present" if artifact_path.exists() else "missing"
    return f"- `{name}`: {status} (`{artifact_path}`)"


def _sampled_segment_texts(state_segments: List[Dict[str, object]], limit: int) -> List[str]:
    samples: List[str] = []
    for segment in state_segments:
        text = str(segment.get("text") or "").replace("\n", " ").strip()
        if not text:
            continue
        samples.append(text)
        if len(samples) >= limit:
            break
    return samples


def build_report(run_dir: Path) -> Path:
    """
    Build a Markdown report for a Markov analysis snapshot directory.

    :param run_dir: Path to the Markov analysis snapshot directory containing ``output.json``.
    :type run_dir: pathlib.Path
    :return: Path to the generated report file.
    :rtype: pathlib.Path
    :raises ValueError: If the run artifacts are malformed.
    """
    output = _load_json(run_dir / "output.json")
    manifest = _load_json(run_dir / "manifest.json")
    report = dict(output["report"])
    snapshot = dict(output.get("snapshot") or manifest)
    configuration = dict(dict(snapshot.get("configuration") or {}).get("config") or {})

    corpus_uri = manifest.get("corpus_uri") or output.get("corpus_uri")
    if not isinstance(corpus_uri, str) or not corpus_uri.startswith("file://"):
        raise ValueError("Expected file:// corpus_uri in output.json or manifest.json")
    corpus_path = Path(corpus_uri.replace("file://", "", 1))
    _load_catalog_items(corpus_path)

    decoded_paths = {
        entry["item_id"]: entry["state_sequence"] for entry in report.get("decoded_paths", [])
    }
    segments = list(_iter_jsonl(run_dir / "segments.jsonl"))
    aligned = _align_segments_to_states(segments=segments, decoded_paths=decoded_paths)
    state_segment_counts = Counter(state_id for state_id, _segment in aligned)
    grouped_segments = _segments_by_state(aligned)
    states = list(report.get("states") or [])
    label_by_state = _state_label_map(states)
    transitions = sorted(
        list(report.get("transitions") or []),
        key=lambda entry: float(entry.get("weight") or 0.0),
        reverse=True,
    )

    lines: List[str] = []
    lines.append("# Markov run report")
    lines.append("")
    lines.append(f"- Run dir: `{run_dir}`")
    lines.append(f"- Corpus: `{corpus_path}`")
    lines.append(
        f"- Run id: `{snapshot.get('snapshot_id') or manifest.get('snapshot_id') or 'unknown'}`"
    )
    lines.append("")
    lines.append("## Run summary")
    lines.append("")
    lines.append(f"- States: {len(states)}")
    lines.append(f"- Transitions: {len(transitions)}")
    lines.append(f"- Items analyzed: {len(decoded_paths)}")
    lines.append(f"- Segments: {len(segments)}")
    lines.append(f"- Observation pipeline: {_observation_description(configuration)}")
    lines.append(
        f"- State naming: {'enabled' if dict(configuration.get('report') or {}).get('state_naming') else 'disabled'}"
    )
    lines.append("")
    lines.append("## Artifact paths")
    lines.append("")
    for name in (
        "segments.jsonl",
        "observations.jsonl",
        "topic_modeling.json",
        "topic_assignments.jsonl",
        "transitions.png",
    ):
        lines.append(_artifact_line(run_dir, name))
    lines.append("")
    lines.append("## State summary")
    lines.append("")
    for state in states:
        state_id = int(state.get("state_id") or 0)
        lines.append(f"- {_state_heading(state)}: {state_segment_counts.get(state_id, 0)} segments")
    lines.append("")
    lines.append("## Transitions")
    lines.append("")
    for transition in transitions:
        from_state = int(transition.get("from_state") or 0)
        to_state = int(transition.get("to_state") or 0)
        weight = float(transition.get("weight") or 0.0)
        lines.append(
            f"- {label_by_state.get(from_state, f'State {from_state}')} (State {from_state}) "
            f"-> {label_by_state.get(to_state, f'State {to_state}')} (State {to_state}): {weight:.4f}"
        )
    lines.append("")
    lines.append("## States")
    lines.append("")
    for state in states:
        state_id = int(state.get("state_id") or 0)
        report_exemplars = [
            str(exemplar).replace("\n", " ").strip()
            for exemplar in list(state.get("exemplars") or [])[:5]
            if str(exemplar).strip()
        ]
        sampled_segments = _sampled_segment_texts(grouped_segments.get(state_id, []), limit=10)
        lines.append(f"### {_state_heading(state)}")
        lines.append("")
        lines.append(f"- Label: `{_state_label(state)}`")
        lines.append(f"- Segment count: {state_segment_counts.get(state_id, 0)}")
        lines.append("- Report exemplars:")
        if report_exemplars:
            for exemplar in report_exemplars:
                lines.append(f"  - {exemplar}")
        else:
            lines.append("  - none")
        lines.append("- Sampled segments:")
        if sampled_segments:
            for sample in sampled_segments:
                lines.append(f"  - {sample}")
        else:
            lines.append("  - none")
        lines.append("")

    report_path = run_dir / "report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    """
    Command-line entrypoint.

    :return: Exit code.
    :rtype: int
    """
    parser = argparse.ArgumentParser(
        description="Generate a Markdown report for a Markov analysis snapshot."
    )
    parser.add_argument(
        "--run-dir", required=True, help="Path to the Markov analysis snapshot directory."
    )
    args = parser.parse_args()
    report_path = build_report(Path(args.run_dir).resolve())
    print(str(report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
