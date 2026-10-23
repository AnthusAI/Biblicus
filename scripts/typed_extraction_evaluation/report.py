"""
Render the scored results as Markdown tables for the evaluation page.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_vocabulary  # noqa: E402


def pct(value: float) -> str:
    """
    Format a ratio as a percentage with one decimal.

    :param value: Ratio between 0 and 1.
    :type value: float
    :return: Formatted percentage.
    :rtype: str
    """
    return f"{value * 100:.1f}"


def table(header, rows) -> str:
    """
    Build a Markdown table.

    :param header: Column titles.
    :type header: list[str]
    :param rows: Row cells.
    :type rows: list[list[str]]
    :return: Markdown table text.
    :rtype: str
    """
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join([" --- "] + [" ---: "] * (len(header) - 1)) + "|",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def render(summaries, vocabulary) -> str:
    """
    Render every table.

    :param summaries: Output of ``score.py``.
    :type summaries: list[dict]
    :param vocabulary: Closed vocabulary.
    :type vocabulary: dict
    :return: Markdown text.
    :rtype: str
    """
    sweep_only = ("gliner2@0.3", "gliner2@0.7", "gliner-medium@0.3", "gliner-medium@0.7")
    primary = [s for s in summaries if s["label"] not in sweep_only]
    primary.sort(key=lambda s: s["label"])
    sweeps = [
        s
        for s in summaries
        if "@0.3" in s["label"] or "@0.7" in s["label"] or s["label"].endswith("@0.5")
    ]
    out = []
    rows = []
    for s in primary:
        e, r = s["entities"]["lenient"], s["relations"]
        rows.append(
            [
                s["label"],
                pct(e["micro"]["precision"]),
                pct(e["micro"]["recall"]),
                pct(e["micro"]["f1"]),
                pct(e["macro_f1"]),
                pct(s["entities"]["strict"]["micro"]["f1"]),
                pct(e["untyped"]["f1"]),
                (
                    "-"
                    if r["micro"]["tp"] + r["micro"]["fp"] == 0
                    else f"{pct(r['micro']['precision'])} / {pct(r['micro']['recall'])} / {pct(r['micro']['f1'])}"
                ),
                f"{s['latency_ms']['median']:.1f}",
                f"{s['latency_ms']['p95']:.1f}",
                (
                    "n/a"
                    if s["cpu_ms"]["median"] == 0 and s["label"] == "llm"
                    else f"{s['cpu_ms']['median']:.1f}"
                ),
                f"{s['api_cost_usd_per_1000_documents']:.2f}",
            ]
        )
    out.append("### Summary\n")
    out.append(
        table(
            [
                "Candidate",
                "Entity P",
                "Entity R",
                "Entity F1",
                "Macro F1",
                "Strict F1",
                "Untyped F1",
                "Relation P / R / F1",
                "Median ms",
                "p95 ms",
                "Median CPU ms",
                "API USD per 1,000 docs",
            ],
            rows,
        )
    )
    kinds = vocabulary["entity_kinds"]
    out.append("\n### Entity precision / recall / F1 per kind (lenient match)\n")
    rows = []
    for s in primary:
        row = [s["label"]]
        for kind in kinds:
            m = s["entities"]["lenient"]["per_kind"][kind]
            row.append(f"{pct(m['precision'])} / {pct(m['recall'])} / {pct(m['f1'])}")
        rows.append(row)
    support = ["gold support"] + [
        str(primary[0]["entities"]["lenient"]["per_kind"][k]["support"]) for k in kinds
    ]
    out.append(table(["Candidate"] + kinds, rows + [support]))
    out.append("\n### Relation precision / recall / F1 per type\n")
    types = vocabulary["relation_types"]
    rows = []
    for s in primary:
        row = [s["label"]]
        for t in types:
            m = s["relations"]["per_type"][t]
            row.append(
                "-"
                if m["tp"] + m["fp"] == 0
                else f"{pct(m['precision'])} / {pct(m['recall'])} / {pct(m['f1'])}"
            )
        rows.append(row)
    support = ["gold support"] + [
        str(primary[0]["relations"]["per_type"][t]["support"]) for t in types
    ]
    out.append(table(["Candidate"] + types, rows + [support]))
    out.append("\n### Entity resolution against the registry (lenient-matched mentions only)\n")
    rows = []
    for s in primary:
        r = s["resolution"]
        known = (
            r.get("known_resolved_correctly", 0)
            + r.get("known_left_unresolved", 0)
            + r.get("known_resolved_to_wrong_entity", 0)
        )
        new = r.get("new_proposed", 0) + r.get("new_wrongly_merged", 0)
        rows.append(
            [
                s["label"],
                str(known),
                str(r.get("known_resolved_correctly", 0)),
                str(r.get("known_left_unresolved", 0)),
                str(r.get("known_resolved_to_wrong_entity", 0)),
                str(new),
                str(r.get("new_wrongly_merged", 0)),
            ]
        )
    out.append(
        table(
            [
                "Candidate",
                "Known entities",
                "Resolved correctly",
                "Unresolved alias",
                "Resolved to wrong entity",
                "New entities",
                "New merged into a known one",
            ],
            rows,
        )
    )
    out.append("\n### Failure modes\n")
    rows = []
    for s in primary:
        f = s["failure_modes"]
        rows.append(
            [
                s["label"],
                str(f["predicted_mentions"]),
                str(f["spurious_no_gold_overlap"]),
                str(f["wrong_kind_overlap"]),
                str(f["ungrounded_text_not_in_source"]),
                str(f["relations_predicted"]),
                str(f["relation_endpoints_not_in_source"]),
                "; ".join(f"{t} x{c}" for t, c in f["top_spurious"][:4]),
            ]
        )
    out.append(
        table(
            [
                "Candidate",
                "Predicted mentions",
                "No gold overlap",
                "Overlap, wrong kind",
                "Text not in source",
                "Relations predicted",
                "Relation endpoints not in source",
                "Most frequent no-overlap predictions",
            ],
            rows,
        )
    )
    out.append("\n### Threshold sensitivity (post-hoc, uses the gold labels, so optimistic)\n")
    rows = []
    for s in sorted(sweeps, key=lambda x: x["label"]):
        if "@" not in s["label"]:
            continue
        e = s["entities"]["lenient"]
        rows.append(
            [
                s["label"],
                pct(e["micro"]["precision"]),
                pct(e["micro"]["recall"]),
                pct(e["micro"]["f1"]),
                pct(s["relations"]["micro"]["f1"]),
            ]
        )
    out.append(
        table(["Candidate and threshold", "Entity P", "Entity R", "Entity F1", "Relation F1"], rows)
    )
    out.append("\n### Versions and configurations\n")
    rows = []
    for s in primary:
        m = s["meta"]
        rows.append(
            [
                s["label"],
                m["version"],
                f"{m['load_seconds']:.1f}",
                f"{m['peak_rss_mb']:.0f}",
                f"{m.get('machine_load_average_at_end', 0):.0f}",
            ]
        )
    out.append(
        table(
            [
                "Candidate",
                "Version and configuration",
                "Load seconds",
                "Peak RSS MB",
                "Load average at end",
            ],
            rows,
        )
    )
    return "\n".join(out) + "\n"


def main() -> int:
    """
    Command-line entry point.

    :return: Process exit status.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    summaries = json.loads(arguments.scores.read_text())
    arguments.out.write_text(render(summaries, load_vocabulary()), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
