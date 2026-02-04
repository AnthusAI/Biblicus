"""
Run the narrative graph extraction demo for all extractors.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]

EXTRACTORS = [
    "simple-entities",
    "cooccurrence",
    "ner-entities",
    "dependency-relations",
]


def _run_extractor(
    *,
    corpus: Path,
    extractor: str,
    limit: int,
    force: bool,
    report_dir: Path | None,
) -> None:
    args: List[str] = [
        "python",
        str(REPO_ROOT / "scripts" / "graph_extraction_extractor_demo.py"),
        "--corpus",
        str(corpus),
        "--extractor",
        extractor,
        "--limit",
        str(limit),
    ]
    if force:
        args.append("--force")
    else:
        args.append("--skip-download")
    if report_dir is not None:
        report_path = report_dir / f"graph_demo_{extractor.replace('-', '_')}.txt"
        args.extend(["--report-path", str(report_path)])
    subprocess.run(args, check=True, cwd=REPO_ROOT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run narrative graph extraction demos for all extractors."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument("--limit", type=int, default=5, help="Number of Wikipedia pages to download.")
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="Optional directory to write per-extractor reports.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    corpus_path = Path(args.corpus).resolve()
    report_dir = Path(args.report_dir).resolve() if args.report_dir else None
    for index, extractor in enumerate(EXTRACTORS):
        _run_extractor(
            corpus=corpus_path,
            extractor=extractor,
            limit=args.limit,
            force=args.force if index == 0 else False,
            report_dir=report_dir,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
