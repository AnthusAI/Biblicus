#!/usr/bin/env python3
"""
Pilot LLM HTML structured extraction on sample web URLs.

Reports method, structured summary, warnings, and timing per URL.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from biblicus.url_text import extract_url_text


DEFAULT_URLS = [
    "https://arxiv.org/abs/1706.03762",
    "https://distill.pub/2017/feature-visualization/",
    "https://jalammar.github.io/illustrated-transformer/",
    "https://lilianweng.github.io/posts/2018-06-24-attention/",
    "https://openai.com/research/attention-is-all-you-need",
]


def _summarize_structured(structured: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(structured, dict):
        return {}
    authors = structured.get("authors") if isinstance(structured.get("authors"), list) else []
    citations = structured.get("citations") if isinstance(structured.get("citations"), list) else []
    with_context = sum(
        1
        for row in citations
        if isinstance(row, dict) and str(row.get("citing_context") or "").strip()
    )
    return {
        "authors_count": len(authors),
        "author_names": [str(a.get("name") or "") for a in authors[:5] if isinstance(a, dict)],
        "publication_date": structured.get("publication_date"),
        "citations_count": len(citations),
        "citations_with_citing_context": with_context,
        "citation_titles_sample": [
            str(row.get("title") or row.get("raw") or "")[:80]
            for row in citations[:5]
            if isinstance(row, dict)
        ],
        "warnings": structured.get("warnings") if isinstance(structured.get("warnings"), list) else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pilot LLM HTML structured URL extraction")
    parser.add_argument("--url", action="append", dest="urls", help="URL to extract (repeatable)")
    parser.add_argument("--output", default="", help="Optional JSON output path")
    args = parser.parse_args()
    urls = args.urls or DEFAULT_URLS

    rows: list[dict[str, Any]] = []
    for url in urls:
        started = time.perf_counter()
        row: dict[str, Any] = {"url": url}
        try:
            result = extract_url_text(source_uri=url)
            elapsed = time.perf_counter() - started
            row.update(
                {
                    "status": result.get("status"),
                    "source_kind": result.get("source_kind"),
                    "method": result.get("method"),
                    "text_length": len(str(result.get("text") or "")),
                    "title": result.get("title"),
                    "elapsed_seconds": round(elapsed, 2),
                    "structured_summary": _summarize_structured(
                        result.get("structured") if isinstance(result.get("structured"), dict) else None
                    ),
                    "error": result.get("error"),
                    "llm_warnings": result.get("llm_structured_warnings"),
                }
            )
        except Exception as exc:
            row.update(
                {
                    "status": "exception",
                    "elapsed_seconds": round(time.perf_counter() - started, 2),
                    "error": f"{exc.__class__.__name__}: {exc}",
                }
            )
        rows.append(row)
        print(json.dumps(row, indent=2, ensure_ascii=False))
        print("---")

    summary = {
        "total": len(rows),
        "ok": sum(1 for row in rows if row.get("status") == "ok"),
        "llm_html": sum(1 for row in rows if row.get("method") == "llm-html"),
        "with_authors": sum(1 for row in rows if (row.get("structured_summary") or {}).get("authors_count")),
        "with_citations": sum(1 for row in rows if (row.get("structured_summary") or {}).get("citations_count")),
        "with_citing_context": sum(
            1
            for row in rows
            if (row.get("structured_summary") or {}).get("citations_with_citing_context")
        ),
    }
    print("SUMMARY", json.dumps(summary, indent=2))

    if args.output:
        payload = {"summary": summary, "rows": rows}
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        print(f"wrote {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
