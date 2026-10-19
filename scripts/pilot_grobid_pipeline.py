#!/usr/bin/env python3
"""
Pilot GROBID pipeline extraction on a sample of PDFs and report quality signals.

Does not run graph extraction — use this to tune text/GROBID behavior before full rebuilds.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from biblicus.configuration import load_configuration_view
from biblicus.corpus import Corpus
from biblicus.extractors import get_extractor
from biblicus.extractors.pipeline import PipelineExtractorConfig
from biblicus.grobid_runtime import ensure_grobid_running
from biblicus.models import ExtractionStageOutput


def _load_pipeline_stages(config_path: Path) -> list[tuple[str, dict[str, Any]]]:
    data = load_configuration_view(
        [str(config_path)],
        configuration_label="extraction config",
        mapping_error_message="expected mapping",
    )
    stages = data.get("configuration", data).get("stages", [])
    if not isinstance(stages, list):
        raise ValueError("pipeline stages missing")
    parsed: list[tuple[str, dict[str, Any]]] = []
    for stage in stages:
        parsed.append((str(stage["extractor_id"]), dict(stage.get("config") or {})))
    return parsed


def _run_pipeline_for_item(
    *,
    corpus: Corpus,
    item,
    stages: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    stage_outputs: list[ExtractionStageOutput] = []
    stage_summaries: list[dict[str, Any]] = []
    for stage_index, (extractor_id, stage_config) in enumerate(stages, start=1):
        extractor = get_extractor(extractor_id)
        parsed_config = extractor.validate_config(stage_config)
        started = time.perf_counter()
        try:
            extracted = extractor.extract_text(
                corpus=corpus,
                item=item,
                config=parsed_config,
                previous_extractions=stage_outputs,
            )
        except Exception as exc:
            return {
                "item_id": item.id,
                "relpath": item.relpath,
                "status": "errored",
                "error": f"{exc.__class__.__name__}: {exc}",
                "stages": stage_summaries,
            }
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if extracted is None:
            stage_summaries.append(
                {
                    "stage_index": stage_index,
                    "extractor_id": extractor_id,
                    "status": "skipped",
                    "elapsed_ms": elapsed_ms,
                }
            )
            continue
        method = str((extracted.metadata or {}).get("method") or "")
        stage_summaries.append(
            {
                "stage_index": stage_index,
                "extractor_id": extractor_id,
                "status": "extracted",
                "producer": extracted.producer_extractor_id,
                "method": method or None,
                "text_chars": len(extracted.text or ""),
                "elapsed_ms": elapsed_ms,
                "grobid_error": (extracted.metadata or {}).get("grobid_fallback"),
            }
        )
        stage_outputs.append(
            ExtractionStageOutput(
                stage_index=stage_index,
                extractor_id=extractor_id,
                status="extracted",
                text=extracted.text,
                text_characters=len(extracted.text or ""),
                producer_extractor_id=extracted.producer_extractor_id,
                source_stage_index=extracted.source_stage_index,
                confidence=extracted.confidence,
                metadata=dict(extracted.metadata or {}),
                error_type=None,
                error_message=None,
            )
        )
    if not stage_outputs:
        return {
            "item_id": item.id,
            "relpath": item.relpath,
            "status": "skipped",
            "stages": stage_summaries,
        }
    select_stage = stages[-1]
    if select_stage[0] == "select-override":
        selector = get_extractor("select-override")
        select_config = selector.validate_config(select_stage[1])
        selected = selector.extract_text(
            corpus=corpus,
            item=item,
            config=select_config,
            previous_extractions=stage_outputs,
        )
        if selected is None:
            return {
                "item_id": item.id,
                "relpath": item.relpath,
                "status": "skipped",
                "stages": stage_summaries,
            }
        final_meta = dict(selected.metadata or {})
        return {
            "item_id": item.id,
            "relpath": item.relpath,
            "status": "extracted",
            "final_producer": selected.producer_extractor_id,
            "final_method": final_meta.get("method"),
            "text_chars": len(selected.text or ""),
            "authors": len((final_meta.get("structured") or {}).get("authors") or []),
            "citations": len((final_meta.get("structured") or {}).get("citations") or []),
            "grobid_fallback": final_meta.get("grobid_fallback"),
            "stages": stage_summaries,
        }
    final = stage_outputs[-1]
    final_meta = dict(final.metadata or {})
    return {
        "item_id": item.id,
        "relpath": item.relpath,
        "status": "extracted",
        "final_producer": final.producer_extractor_id,
        "final_method": final_meta.get("method"),
        "text_chars": len(final.text or ""),
        "authors": len((final_meta.get("structured") or {}).get("authors") or []),
        "citations": len((final_meta.get("structured") or {}).get("citations") or []),
        "grobid_fallback": final_meta.get("grobid_fallback"),
        "stages": stage_summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="corpora/AI-ML-research")
    parser.add_argument(
        "--configuration",
        default="configurations/extraction/ai-ml-research-topic-text.yml",
    )
    parser.add_argument("--sample-size", type=int, default=25)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel items (simulates extract build worker pool).",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    ensure_grobid_running()
    corpus = Corpus.open(args.corpus)
    catalog = corpus.load_catalog()
    pdf_items = [
        corpus.get_item(item_id)
        for item_id, entry in catalog.items.items()
        if entry.media_type == "application/pdf"
    ]
    sample = random.Random(args.seed).sample(pdf_items, min(args.sample_size, len(pdf_items)))
    stages = _load_pipeline_stages(Path(args.configuration))

    results: list[dict[str, Any]] = []
    started = time.perf_counter()
    workers = max(1, int(args.workers))

    def _run_one(item) -> dict[str, Any]:
        return _run_pipeline_for_item(corpus=corpus, item=item, stages=stages)

    if workers == 1:
        for index, item in enumerate(sample, start=1):
            print(f"[pilot] {index}/{len(sample)} {item.relpath}", flush=True)
            results.append(_run_one(item))
    else:
        print(f"[pilot] running {len(sample)} items with {workers} workers", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_run_one, item): item for item in sample}
            done = 0
            for future in as_completed(futures):
                done += 1
                item = futures[future]
                row = future.result()
                results.append(row)
                print(
                    f"[pilot] {done}/{len(sample)} {item.relpath} method={row.get('final_method')}",
                    flush=True,
                )

    methods = Counter(row.get("final_method") or "none" for row in results if row.get("status") == "extracted")
    fallbacks = [
        row
        for row in results
        if row.get("final_method") == "pypdf-fallback" or row.get("grobid_fallback")
    ]
    grobid_ok = [
        row
        for row in results
        if row.get("final_method") == "grobid" and row.get("text_chars", 0) > 0
    ]
    summary = {
        "sample_size": len(sample),
        "elapsed_seconds": round(time.perf_counter() - started, 1),
        "status_counts": dict(Counter(row.get("status") for row in results)),
        "final_methods": dict(methods),
        "grobid_success": len(grobid_ok),
        "pypdf_fallback": len(fallbacks),
        "grobid_success_rate": round(len(grobid_ok) / max(len(sample), 1), 3),
        "avg_authors": round(
            sum(row.get("authors", 0) for row in grobid_ok) / max(len(grobid_ok), 1),
            1,
        ),
        "avg_citations": round(
            sum(row.get("citations", 0) for row in grobid_ok) / max(len(grobid_ok), 1),
            1,
        ),
        "fallback_samples": [
            {
                "relpath": row.get("relpath"),
                "grobid_fallback": row.get("grobid_fallback"),
            }
            for row in fallbacks[:8]
        ],
        "items": results,
    }
    output_path = args.output or Path("/tmp/biblicus-grobid-pilot.json")
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "items"}, indent=2))
    print(f"wrote {output_path}")
    return 0 if len(grobid_ok) >= max(1, len(sample) // 2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
