#!/usr/bin/env python3
"""
Probe GROBID extraction health on a sample of corpus PDFs.

Auto-starts local GROBID via Docker when needed (same as corpus extraction).
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from biblicus.grobid_runtime import ensure_grobid_running
from biblicus.url_text import UrlTextExtractionError, _convert_pdf_with_grobid


def _probe_one(*, root: Path, item: dict) -> tuple[str, float, str | None]:
    path = root / item["relpath"]
    started = time.perf_counter()
    try:
        payload = _convert_pdf_with_grobid(
            data=path.read_bytes(),
            source_uri=str(path),
            content_type=item.get("media_type"),
        )
        text = str(payload.get("text") or "").strip()
        if not text:
            return "empty", time.perf_counter() - started, None
        structured = payload.get("structured") if isinstance(payload.get("structured"), dict) else {}
        authors = len(structured.get("authors") or [])
        return "ok", time.perf_counter() - started, f"authors={authors}"
    except UrlTextExtractionError as exc:
        return exc.code, time.perf_counter() - started, exc.message


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="corpora/AI-ML-research")
    parser.add_argument("--sample-size", type=int, default=12)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    root = Path(args.corpus)
    ensure_grobid_running()
    catalog = json.loads((root / "metadata" / "catalog.json").read_text(encoding="utf-8"))
    items = [value for value in catalog["items"].values() if value.get("media_type") == "application/pdf"]
    if not items:
        raise SystemExit("No PDF items found in catalog.")
    sample = random.Random(args.seed).sample(items, min(args.sample_size, len(items)))

    results: list[tuple[str, float, str | None]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [
            executor.submit(_probe_one, root=root, item=item)
            for item in sample
        ]
        for future in as_completed(futures):
            results.append(future.result())

    status_counts = Counter(status for status, _elapsed, _detail in results)
    error_codes = Counter(status for status, _elapsed, _detail in results if status not in {"ok", "empty"})
    avg_seconds = sum(elapsed for _status, elapsed, _detail in results) / max(len(results), 1)
    summary = {
        "sample_size": len(results),
        "workers": args.workers,
        "status_counts": dict(status_counts),
        "error_codes": dict(error_codes),
        "avg_seconds": round(avg_seconds, 2),
        "recommendation": (
            "GROBID looks healthy for a small sample."
            if status_counts.get("ok", 0) >= max(1, len(results) // 2)
            else "GROBID is failing for most samples — fix service health before corpus rebuild."
        ),
    }
    print(json.dumps(summary, indent=2))
    return 0 if status_counts.get("ok", 0) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
