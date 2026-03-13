"""
Generate a Markdown report for a topic modeling analysis snapshot.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def _load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(run_dir: Path) -> Path:
    """
    Build a Markdown report for a topic modeling analysis snapshot directory.

    :param run_dir: Path to the topic modeling analysis snapshot directory.
    :type run_dir: pathlib.Path
    :return: Path to the generated report file.
    :rtype: pathlib.Path
    """
    output = _load_json(run_dir / "output.json")
    snapshot = dict(output.get("snapshot") or {})
    report = dict(output.get("report") or {})
    topics = sorted(
        list(report.get("topics") or []),
        key=lambda entry: (-int(entry.get("document_count") or 0), int(entry.get("topic_id") or 0)),
    )
    outlier_count = sum(
        int(topic.get("document_count") or 0)
        for topic in topics
        if int(topic.get("topic_id") or 0) == -1
    )

    lines: List[str] = []
    lines.append("# Topic modeling run report")
    lines.append("")
    lines.append(f"- Run dir: `{run_dir}`")
    lines.append(f"- Corpus: `{snapshot.get('corpus_uri') or 'unknown'}`")
    lines.append(f"- Run id: `{snapshot.get('snapshot_id') or 'unknown'}`")
    lines.append("")
    lines.append("## Run summary")
    lines.append("")
    text_collection = dict(report.get("text_collection") or {})
    bertopic_analysis = dict(report.get("bertopic_analysis") or {})
    lines.append(f"- Source items: {int(text_collection.get('source_items') or 0)}")
    lines.append(f"- Documents analyzed: {int(bertopic_analysis.get('document_count') or 0)}")
    lines.append(f"- Topics discovered: {int(bertopic_analysis.get('topic_count') or 0)}")
    lines.append(f"- Outlier documents: {outlier_count}")
    lines.append("")
    lines.append("## Topics")
    lines.append("")
    for topic in topics:
        topic_id = int(topic.get("topic_id") or 0)
        label = str(topic.get("label") or f"Topic {topic_id}")
        label_source = str(topic.get("label_source") or "unknown")
        document_count = int(topic.get("document_count") or 0)
        keywords = list(topic.get("keywords") or [])[:10]
        examples = [
            str(example).strip()
            for example in list(topic.get("document_examples") or [])[:5]
            if str(example).strip()
        ]
        lines.append(f"### {label} (Topic {topic_id})")
        lines.append("")
        lines.append(f"- Label source: `{label_source}`")
        lines.append(f"- Document count: {document_count}")
        lines.append("- Keywords:")
        if keywords:
            for keyword in keywords:
                lines.append(
                    f"  - {str(keyword.get('keyword') or '').strip()}: {float(keyword.get('score') or 0.0):.4f}"
                )
        else:
            lines.append("  - none")
        lines.append("- Representative examples:")
        if examples:
            for example in examples:
                lines.append(f"  - {example}")
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
        description="Generate a Markdown report for a topic modeling analysis snapshot."
    )
    parser.add_argument(
        "--run-dir", required=True, help="Path to the topic modeling analysis snapshot directory."
    )
    args = parser.parse_args()
    report_path = build_report(Path(args.run_dir).resolve())
    print(str(report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
