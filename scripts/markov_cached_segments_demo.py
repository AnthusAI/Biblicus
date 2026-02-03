"""
Snapshot Markov analysis with cached span-markup segmentation.

This demo script performs the span-markup segmentation once, caches the marked-up text and
segments, and reuses that cache for subsequent HMM snapshots. It keeps caching in application-level
code rather than the text utilities or analysis backend.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from biblicus.analysis.markov import (
    MarkovBackend,
    _add_boundary_segments,
    _analysis_snapshot_id,
    _assign_state_names,
    _build_observations,
    _build_states,
    _collect_documents,
    _create_configuration_manifest,
    _encode_observations,
    _fit_and_decode,
    _group_decoded_paths,
    _write_analysis_snapshot_manifest,
    _write_graphviz,
    _write_observations,
    _write_segments,
    _write_transitions_json,
)
from biblicus.analysis.models import (
    AnalysisSnapshotInput,
    AnalysisSnapshotManifest,
    MarkovAnalysisConfiguration,
    MarkovAnalysisOutput,
    MarkovAnalysisReport,
    MarkovAnalysisSegment,
    MarkovAnalysisSegmentationMethod,
    MarkovAnalysisStageStatus,
    MarkovAnalysisTextCollectionReport,
)
from biblicus.configuration import (
    apply_dotted_overrides,
    load_configuration_view,
    parse_dotted_overrides,
)
from biblicus.corpus import Corpus
from biblicus.models import ExtractionSnapshotReference, parse_extraction_snapshot_reference
from biblicus.retrieval import hash_text
from biblicus.text.annotate import TextAnnotateRequest, apply_text_annotate
from biblicus.text.extract import TextExtractRequest, apply_text_extract
from biblicus.time import utc_now_iso

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _parse_list(raw: Optional[Iterable[str]]) -> List[str]:
    """
    Parse a repeatable argument list into a normalized list.

    :param raw: Iterable of raw argument values.
    :type raw: Iterable[str] or None
    :return: Normalized list.
    :rtype: list[str]
    """
    if raw is None:
        return []
    values = [str(value).strip() for value in raw if str(value).strip()]
    return values


def _load_configuration_config(
    *, configuration_paths: List[str], overrides: Dict[str, object]
) -> MarkovAnalysisConfiguration:
    """
    Load and validate a Markov analysis configuration configuration.

    :param configuration_paths: Ordered list of configuration file paths.
    :type configuration_paths: list[str]
    :param overrides: Dotted key overrides applied after composition.
    :type overrides: dict[str, object]
    :return: Validated configuration configuration.
    :rtype: MarkovAnalysisConfiguration
    """
    view = load_configuration_view(configuration_paths, configuration_label="Configuration file")
    if overrides:
        view = apply_dotted_overrides(view, overrides)
    return MarkovAnalysisConfiguration.model_validate(view)


def _segmentation_signature(*, config: MarkovAnalysisConfiguration) -> str:
    segmentation_payload = config.segmentation.model_dump()
    span_markup = segmentation_payload.get("span_markup")
    if isinstance(span_markup, dict):
        span_markup.pop("start_label_value", None)
        span_markup.pop("end_label_value", None)
        span_markup.pop("end_reject_label_value", None)
        span_markup.pop("end_reject_reason_prefix", None)
        span_markup.pop("end_label_verifier", None)
    payload = {
        "min_text_characters": config.text_source.min_text_characters,
        "segmentation": segmentation_payload,
    }
    return hash_text(json.dumps(payload, sort_keys=True))


def _cache_root(*, corpus_path: Path, override: Optional[str]) -> Path:
    if override:
        return Path(override).resolve()
    return corpus_path / ".biblicus" / "demo_cache" / "markov" / "segments"


def _load_cached_segments(
    *, cache_dir: Path
) -> Tuple[List[MarkovAnalysisSegment], Dict[str, object]]:
    segments_path = cache_dir / "segments.jsonl"
    manifest_path = cache_dir / "cache_manifest.json"
    if not segments_path.exists() or not manifest_path.exists():
        raise FileNotFoundError("Cached segments not found")
    segments: List[MarkovAnalysisSegment] = []
    for line in segments_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        segments.append(MarkovAnalysisSegment.model_validate_json(line))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return segments, manifest


def _write_cache_manifest(*, cache_dir: Path, payload: Dict[str, object]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "cache_manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _write_marked_up_texts(*, cache_dir: Path, records: Sequence[Dict[str, str]]) -> None:
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    (cache_dir / "marked_up_texts.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _segment_with_markup(
    *,
    item_id: str,
    text: str,
    config: MarkovAnalysisConfiguration,
) -> Tuple[List[Dict[str, object]], str]:
    markup_config = config.segmentation.span_markup
    if markup_config is None:
        raise ValueError("segmentation.span_markup is required for span-markup segmentation")
    label_attribute = markup_config.label_attribute
    prepend_label = markup_config.prepend_label

    if label_attribute is not None or prepend_label:
        request = TextAnnotateRequest(
            text=text,
            client=markup_config.client,
            prompt_template=markup_config.prompt_template,
            system_prompt=markup_config.system_prompt,
            allowed_attributes=[label_attribute] if label_attribute else None,
            max_rounds=markup_config.max_rounds,
            max_edits_per_round=markup_config.max_edits_per_round,
        )
        result = apply_text_annotate(request)
    else:
        request = TextExtractRequest(
            text=text,
            client=markup_config.client,
            prompt_template=markup_config.prompt_template,
            system_prompt=markup_config.system_prompt,
            max_rounds=markup_config.max_rounds,
            max_edits_per_round=markup_config.max_edits_per_round,
        )
        result = apply_text_extract(request)

    segment_payloads: List[Dict[str, object]] = []
    for index, span in enumerate(result.spans, start=1):
        segment_body = str(span.text).strip()
        if not segment_body:
            continue
        segment_text = segment_body
        if prepend_label:
            if label_attribute is None:
                raise ValueError(
                    "segmentation.span_markup.label_attribute is required when "
                    "segmentation.span_markup.prepend_label is true"
                )
            label_value = str(span.attributes.get(label_attribute, "")).strip()
            if not label_value:
                raise ValueError(f"Span {index} missing label attribute '{label_attribute}'")
            segment_text = f"{label_value}\n{segment_body}"
        segment_payloads.append(
            {"segment_index": index, "body": segment_body, "text": segment_text}
        )
    return segment_payloads, result.marked_up_text


def _payloads_from_cache(
    *,
    raw_segments: object,
    prepend_label: bool,
) -> List[Dict[str, object]]:
    """
    Normalize cached segment payloads into dict payloads.

    :param raw_segments: Cached segment data.
    :type raw_segments: object
    :param prepend_label: Whether labels are prepended in segment text.
    :type prepend_label: bool
    :return: Normalized payload list.
    :rtype: list[dict[str, object]]
    """
    if not isinstance(raw_segments, list):
        return []
    payloads: List[Dict[str, object]] = []
    for index, entry in enumerate(raw_segments, start=1):
        if isinstance(entry, dict):
            text_value = str(entry.get("text", "")).strip()
            body_value = str(entry.get("body", "")).strip()
        else:
            text_value = str(entry).strip()
            body_value = text_value
            if prepend_label and text_value:
                lines = text_value.splitlines()
                if len(lines) > 1:
                    body_value = "\n".join(lines[1:]).strip()
        if not text_value:
            continue
        payloads.append({"segment_index": index, "body": body_value, "text": text_value})
    return payloads


def _build_cached_segments(
    *,
    corpus: Corpus,
    extraction_snapshot: ExtractionSnapshotReference,
    config: MarkovAnalysisConfiguration,
    cache_dir: Path,
    workers: int,
    refresh_cache: bool,
) -> Tuple[List[MarkovAnalysisSegment], Dict[str, object]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    item_cache_dir = cache_dir / "items"
    item_cache_dir.mkdir(parents=True, exist_ok=True)
    signature = _segmentation_signature(config=config)
    documents, text_report = _collect_documents(
        corpus=corpus,
        extraction_snapshot=extraction_snapshot,
        config=config.text_source,
    )

    def process_document(
        document: object,
    ) -> Tuple[str, List[Dict[str, object]], str, Optional[str]]:
        item_cache_path = item_cache_dir / f"{document.item_id}.json"
        if item_cache_path.exists() and not refresh_cache:
            cached_payload = json.loads(item_cache_path.read_text(encoding="utf-8"))
            if cached_payload.get("signature") != signature:
                cached_payload = {}
            cached_payloads = _payloads_from_cache(
                raw_segments=cached_payload.get("segments", []),
                prepend_label=bool(config.segmentation.span_markup.prepend_label),
            )
            cached_marked_up_text = str(cached_payload.get("marked_up_text", "")).strip()
            if cached_payloads and cached_marked_up_text:
                return (
                    document.item_id,
                    cached_payloads,
                    cached_marked_up_text,
                    None,
                )
        try:
            payloads, marked_up_text = _segment_with_markup(
                item_id=document.item_id,
                text=document.text,
                config=config,
            )
        except Exception as exc:
            item_payload = {
                "item_id": document.item_id,
                "signature": signature,
                "error": str(exc),
                "marked_up_text": "",
                "segments": [],
            }
            item_cache_path.write_text(json.dumps(item_payload, indent=2) + "\n", encoding="utf-8")
            return document.item_id, [], "", str(exc)
        item_payload = {
            "item_id": document.item_id,
            "signature": signature,
            "marked_up_text": marked_up_text,
            "segments": payloads,
        }
        item_cache_path.write_text(json.dumps(item_payload, indent=2) + "\n", encoding="utf-8")
        return document.item_id, payloads, marked_up_text, None

    results: Dict[str, Tuple[List[Dict[str, object]], str]] = {}
    segmentation_errors: List[str] = []
    if workers <= 1:
        for document in documents:
            item_id, payloads, marked_up_text, error = process_document(document)
            if error:
                segmentation_errors.append(f"{item_id}: {error}")
            results[item_id] = (payloads, marked_up_text)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(process_document, document): document for document in documents
            }
            for future in as_completed(futures):
                item_id, payloads, marked_up_text, error = future.result()
                if error:
                    segmentation_errors.append(f"{item_id}: {error}")
                results[item_id] = (payloads, marked_up_text)

    segments: List[MarkovAnalysisSegment] = []
    marked_up_texts: List[Dict[str, str]] = []
    for document in documents:
        payloads, marked_up_text = results[document.item_id]
        if not payloads:
            continue
        doc_segments = [
            MarkovAnalysisSegment(
                item_id=document.item_id,
                segment_index=int(payload["segment_index"]),
                text=str(payload["text"]),
            )
            for payload in payloads
            if str(payload["text"]).strip()
        ]
        if not doc_segments:
            continue
        segments.extend(doc_segments)
        marked_up_texts.append({"item_id": document.item_id, "marked_up_text": marked_up_text})
    if segmentation_errors:
        warnings = list(text_report.warnings) + segmentation_errors
        text_report = text_report.model_copy(update={"warnings": warnings})
    segments_with_boundaries = _add_boundary_segments(segments=segments)
    _write_segments(snapshot_dir=cache_dir, segments=segments_with_boundaries)
    _write_marked_up_texts(cache_dir=cache_dir, records=marked_up_texts)
    manifest_payload: Dict[str, object] = {
        "cache_id": cache_dir.name,
        "created_at": utc_now_iso(),
        "extraction_snapshot": extraction_snapshot.as_string(),
        "catalog_generated_at": corpus.load_catalog().generated_at,
        "text_collection": text_report.model_dump(),
        "text_source": config.text_source.model_dump(),
        "min_text_characters": config.text_source.min_text_characters,
        "segmentation": config.segmentation.model_dump(),
        "signature": signature,
        "segment_count": len(segments_with_boundaries),
        "item_count": len({segment.item_id for segment in segments_with_boundaries}),
    }
    _write_cache_manifest(cache_dir=cache_dir, payload=manifest_payload)
    return segments_with_boundaries, manifest_payload


def _snapshot_hmm_from_segments(
    *,
    corpus: Corpus,
    configuration_name: str,
    config: MarkovAnalysisConfiguration,
    extraction_snapshot: ExtractionSnapshotReference,
    segments: Sequence[MarkovAnalysisSegment],
    text_collection_payload: Dict[str, object],
) -> Dict[str, object]:
    configuration_manifest = _create_configuration_manifest(name=configuration_name, config=config)
    catalog = corpus.load_catalog()
    snapshot_id = _analysis_snapshot_id(
        configuration_id=configuration_manifest.configuration_id,
        extraction_snapshot=extraction_snapshot,
        catalog_generated_at=catalog.generated_at,
    )
    snapshot_manifest = AnalysisSnapshotManifest(
        snapshot_id=snapshot_id,
        configuration=configuration_manifest,
        corpus_uri=catalog.corpus_uri,
        catalog_generated_at=catalog.generated_at,
        created_at=utc_now_iso(),
        input=AnalysisSnapshotInput(extraction_snapshot=extraction_snapshot),
        artifact_paths=[],
        stats={},
    )
    snapshot_dir = corpus.analysis_snapshot_dir(
        analysis_id=MarkovBackend.analysis_id, snapshot_id=snapshot_id
    )
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    observations = _build_observations(segments=segments, config=config)
    observation_matrix, lengths = _encode_observations(observations=observations, config=config)
    predicted_states, transitions, state_count = _fit_and_decode(
        observations=observation_matrix,
        lengths=lengths,
        config=config,
    )
    decoded_paths = _group_decoded_paths(segments=segments, predicted_states=predicted_states)
    states = _build_states(
        segments=segments,
        predicted_states=predicted_states,
        n_states=state_count,
        max_exemplars=config.report.max_state_exemplars,
    )
    states = _assign_state_names(states=states, config=config)

    artifact_paths: List[str] = [
        "output.json",
        "segments.jsonl",
        "observations.jsonl",
        "transitions.json",
    ]
    _write_segments(snapshot_dir=snapshot_dir, segments=segments)
    _write_observations(snapshot_dir=snapshot_dir, observations=observations)
    _write_transitions_json(snapshot_dir=snapshot_dir, transitions=transitions)

    if config.artifacts.graphviz.enabled:
        _write_graphviz(
            snapshot_dir=snapshot_dir,
            transitions=transitions,
            graphviz=config.artifacts.graphviz,
            states=states,
            decoded_paths=decoded_paths,
        )
        artifact_paths.append("transitions.dot")

    text_collection_payload = dict(text_collection_payload)
    if "status" in text_collection_payload:
        status_value = text_collection_payload["status"]
        if isinstance(status_value, MarkovAnalysisStageStatus):
            text_collection_payload["status"] = status_value
        else:
            status_text = str(status_value)
            try:
                text_collection_payload["status"] = MarkovAnalysisStageStatus(status_text)
            except ValueError:
                if "." in status_text:
                    status_text = status_text.split(".")[-1]
                text_collection_payload["status"] = MarkovAnalysisStageStatus(status_text.lower())
    text_collection_report = MarkovAnalysisTextCollectionReport.model_validate(
        text_collection_payload
    )
    report = MarkovAnalysisReport(
        text_collection=text_collection_report,
        status=MarkovAnalysisStageStatus.COMPLETE,
        states=states,
        transitions=transitions,
        decoded_paths=decoded_paths,
        warnings=list(text_collection_report.warnings),
        errors=list(text_collection_report.errors),
    )
    output = MarkovAnalysisOutput(
        analysis_id=MarkovBackend.analysis_id,
        generated_at=utc_now_iso(),
        snapshot=snapshot_manifest,
        report=report,
    )

    snapshot_stats = {
        "items": len({segment.item_id for segment in segments}),
        "segments": len(segments),
        "states": len(states),
        "transitions": len(transitions),
    }
    snapshot_manifest = snapshot_manifest.model_copy(
        update={"artifact_paths": artifact_paths, "stats": snapshot_stats}
    )
    _write_analysis_snapshot_manifest(snapshot_dir=snapshot_dir, manifest=snapshot_manifest)
    (snapshot_dir / "output.json").write_text(
        output.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    return {
        "snapshot_id": snapshot_id,
        "snapshot_dir": str(snapshot_dir),
        "output_path": str(snapshot_dir / "output.json"),
        "transitions_dot": (
            str(snapshot_dir / "transitions.dot")
            if (snapshot_dir / "transitions.dot").is_file()
            else None
        ),
        "stats": snapshot_stats,
    }


def snapshot_demo(arguments: argparse.Namespace) -> Dict[str, object]:
    """
    Execute the cached segmentation Markov demo workflow.

    :param arguments: Parsed command-line arguments.
    :type arguments: argparse.Namespace
    :return: Demo summary.
    :rtype: dict[str, object]
    """
    corpus_path = Path(arguments.corpus).resolve()
    corpus_config = corpus_path / ".biblicus" / "config.json"
    if not corpus_config.exists():
        raise SystemExit(
            "Corpus not initialized. Initialize a corpus or pass a valid corpus path with .biblicus/config.json."
        )

    corpus = Corpus.open(corpus_path)
    extraction_snapshot = parse_extraction_snapshot_reference(arguments.extraction_snapshot)

    overrides = parse_dotted_overrides(_parse_list(arguments.config))
    configuration_paths = _parse_list(arguments.configuration) or [
        str(REPO_ROOT / "configurations" / "markov" / "openai-enriched.yml")
    ]
    config = _load_configuration_config(
        configuration_paths=configuration_paths, overrides=overrides
    )
    if config.segmentation.method != MarkovAnalysisSegmentationMethod.SPAN_MARKUP:
        raise SystemExit("This demo expects segmentation.method to be span_markup.")

    cache_root = _cache_root(corpus_path=corpus_path, override=arguments.cache_dir)
    cache_dir = cache_root

    segments, manifest_payload = _build_cached_segments(
        corpus=corpus,
        extraction_snapshot=extraction_snapshot,
        config=config,
        cache_dir=cache_dir,
        workers=arguments.workers,
        refresh_cache=arguments.refresh_cache,
    )

    hmm_summary = _snapshot_hmm_from_segments(
        corpus=corpus,
        configuration_name=arguments.configuration_name,
        config=config,
        extraction_snapshot=extraction_snapshot,
        segments=segments,
        text_collection_payload=manifest_payload.get("text_collection", {}),
    )

    return {
        "corpus": str(corpus_path),
        "extraction_snapshot": extraction_snapshot.as_string(),
        "configuration_paths": configuration_paths,
        "cache_dir": str(cache_dir),
        "marked_up_texts": str(cache_dir / "marked_up_texts.jsonl"),
        "segments": str(cache_dir / "segments.jsonl"),
        "analysis": hmm_summary,
    }


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Snapshot Markov analysis with cached span-markup segmentation."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to analyze.")
    parser.add_argument(
        "--extraction-snapshot",
        required=True,
        help="Extraction snapshot reference (e.g. pipeline:<snapshot_id>).",
    )
    parser.add_argument(
        "--configuration",
        action="append",
        help="Markov configuration path (repeatable; later configurations override earlier ones).",
    )
    parser.add_argument(
        "--configuration-name",
        default="cached-span-markup",
        help="Configuration name stored in the analysis snapshot manifest.",
    )
    parser.add_argument(
        "--cache-dir",
        help="Override the cache directory (defaults to .biblicus/demo_cache/markov/segments).",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Rebuild cached segmentation even if it already exists.",
    )
    parser.add_argument(
        "--config",
        action="append",
        help="Dotted config override key=value (repeatable; applied after configuration composition).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent workers for span-markup processing.",
    )
    return parser


def main() -> int:
    """
    Script entry point.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()
    summary = snapshot_demo(args)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
