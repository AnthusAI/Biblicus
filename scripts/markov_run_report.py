"""
Generate a human-readable report for a Markov analysis run.

This script is intentionally pragmatic: it turns Biblicus' structured Markov artifacts into a small Markdown report
that a human can read and click through while iterating on recipes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _label_for_item(catalog_items: Dict[str, Dict[str, object]], item_id: str) -> str:
    entry = catalog_items.get(item_id, {})
    tags = entry.get("tags") or []
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("label:"):
                return tag
    return "label:unknown"


def _align_segments_to_states(
    *, segments: List[Dict[str, object]], decoded_paths: Dict[str, List[int]]
) -> List[Tuple[int, Dict[str, object]]]:
    aligned: List[Tuple[int, Dict[str, object]]] = []
    by_item: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for seg in segments:
        item_id = str(seg.get("item_id") or "")
        if not item_id:
            continue
        by_item[item_id].append(seg)
    for item_id, segs in by_item.items():
        seq = decoded_paths.get(item_id)
        if seq is None:
            continue
        segs_sorted = sorted(segs, key=lambda s: int(s.get("segment_index") or 0))
        for seg, state in zip(segs_sorted, seq):
            aligned.append((int(state), seg))
    return aligned


def _segments_by_state(
    aligned: List[Tuple[int, Dict[str, object]]],
) -> Dict[int, List[Dict[str, object]]]:
    grouped: Dict[int, List[Dict[str, object]]] = defaultdict(list)
    for state_id, segment in aligned:
        grouped[state_id].append(segment)
    return grouped


def build_report(run_dir: Path) -> Path:
    output = _load_json(run_dir / "output.json")
    report = output["report"]

    decoded = {p["item_id"]: p["state_sequence"] for p in report["decoded_paths"]}
    segments = list(_iter_jsonl(run_dir / "segments.jsonl"))

    corpus_uri = output["run"]["corpus_uri"]
    if not isinstance(corpus_uri, str) or not corpus_uri.startswith("file://"):
        raise ValueError("Expected file:// corpus_uri in output.json")
    corpus_path = Path(corpus_uri.replace("file://", "", 1))
    catalog = _load_json(corpus_path / ".biblicus" / "catalog.json")
    catalog_items = catalog["items"]
    if not isinstance(catalog_items, dict):
        raise ValueError("Expected catalog.items to be a mapping")

    label_counts = Counter()
    for item_id in decoded:
        label_counts[_label_for_item(catalog_items, item_id)] += 1

    aligned = _align_segments_to_states(segments=segments, decoded_paths=decoded)
    state_segment_counts = Counter(state for state, _ in aligned)
    segments_by_state = _segments_by_state(aligned)

    lines: List[str] = []
    lines.append("# Markov run report")
    lines.append("")
    lines.append(f"- Run dir: `{run_dir}`")
    lines.append(f"- Corpus: `{corpus_path}`")
    lines.append(f"- Run id: `{output['run']['run_id']}`")
    lines.append("")
    lines.append("## What this run learned (high level)")
    lines.append("")
    transitions = report["transitions"]
    lines.append(f"- States: {len(report['states'])}")
    lines.append(f"- Transitions: {len(transitions)}")
    lines.append(f"- Items analyzed: {len(decoded)}")
    lines.append(f"- Segments: {len(segments)} (aligned: {sum(state_segment_counts.values())})")
    lines.append("")
    lines.append("## Corpus label mix (from catalog tags)")
    lines.append("")
    for label, count in label_counts.most_common():
        lines.append(f"- {label}: {count}")
    lines.append("")
    lines.append("## Transitions (graph edges)")
    lines.append("")
    for edge in transitions:
        lines.append(
            f"- {edge['from_state']} -> {edge['to_state']}: {edge['weight']:.4f}"
        )
    lines.append("")
    lines.append("## States (how to interpret)")
    lines.append("")
    lines.append(
        "These are *latent* states learned from the observation vectors (here: TF-IDF over fixed windows). "
        "They are not pre-named phases. Interpret them by looking at exemplars and by inspecting segments "
        "assigned to each state."
    )
    lines.append(
        "If a state has only a few exemplars, it usually means the state has very few segments in this run."
    )
    lines.append("")

    for state in report["states"]:
        state_id = state["state_id"]
        state_segments = segments_by_state.get(state_id, [])
        lines.append(f"### State {state_id}")
        lines.append("")
        lines.append(f"- Segment count: {state_segment_counts.get(state_id, 0)}")
        lines.append("- Exemplars (from the report):")
        report_exemplars = list(state.get("exemplars") or [])
        for ex in report_exemplars[:5]:
            snippet = str(ex).replace("\n", " ")
            lines.append(f"  - {snippet}")
        remaining = 12
        sampled: List[str] = []
        for segment in state_segments:
            text = str(segment.get("text") or "").replace("\n", " ").strip()
            if not text:
                continue
            sampled.append(text)
            if len(sampled) >= remaining:
                break
        if sampled:
            lines.append("- Exemplars (sampled from segments):")
            for snippet in sampled:
                lines.append(f"  - {snippet}")
        if not report_exemplars and not sampled:
            lines.append("- Exemplars: none (no segments assigned)")
        lines.append("")

    # Sports drill-down: show a few example items and their state-labeled segments.
    sports_items = [
        item_id
        for item_id in decoded.keys()
        if "label:Sports" in (catalog_items[item_id].get("tags") or [])
    ]
    lines.append("## Sports slice (example drill-down)")
    lines.append("")
    lines.append(f"- Sports items in this run: {len(sports_items)}")
    lines.append("")
    example_items = sports_items[:3]
    for item_id in example_items:
        entry = catalog_items.get(item_id, {})
        title = entry.get("title") or ""
        lines.append(f"### Item {item_id}")
        if title:
            lines.append(f"- Title: {title}")
        lines.append(f"- Decoded states: {decoded[item_id]}")
        lines.append("- Segments:")
        segs = [s for s in segments if s.get("item_id") == item_id]
        segs = sorted(segs, key=lambda s: int(s.get("segment_index") or 0))
        for seg, st in zip(segs, decoded[item_id]):
            text = str(seg.get("text") or "").replace("\n", " ")
            lines.append(f"  - state {st}: {text}")
        lines.append("")

    lines.append("## Example input text")
    lines.append("")
    example_item_id = next(iter(decoded.keys()), None)
    if example_item_id is None:
        lines.append("No input items found for this run.")
    else:
        entry = catalog_items.get(example_item_id, {})
        relpath = entry.get("relpath")
        lines.append(f"- Item id: {example_item_id}")
        if relpath:
            lines.append(f"- Source path: `{corpus_path / relpath}`")
            try:
                raw_text = (corpus_path / relpath).read_text(encoding='utf-8').strip()
            except Exception:
                raw_text = ""
            if raw_text:
                lines.append("")
                lines.append("```\n" + raw_text + "\n```")
            else:
                lines.append("- Source text unavailable")
        else:
            lines.append("- Source path unavailable")

    report_path = run_dir / "report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Markdown report for a Markov analysis run.")
    parser.add_argument("--run-dir", required=True, help="Path to the Markov analysis run directory.")
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    report_path = build_report(run_dir)
    print(str(report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
