"""
Run one candidate extractor over the whole evaluation set under the shared protocol.

Protocol: documents are processed one at a time on CPU after three untimed warm-up documents.
The registry of known entities for each document is built from the gold labels of the other half of the
publication's items (items alternate between two folds), so no candidate ever sees the gold labels of
the document it extracts. Alias resolution against that registry is applied identically to every candidate by the scoring step.
"""

import argparse
import json
import os
import re
import resource
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidates import (  # noqa: E402
    GazetteerCandidate,
    Gliner2Candidate,
    GlinerCandidate,
    GlirelCandidate,
    HybridCandidate,
    LlmCandidate,
    Registry,
    RelexCandidate,
    SpacyCandidate,
)
from common import LAB_DIRECTORY, load_jsonl, load_vocabulary  # noqa: E402

GLINER_MODELS = {
    "gliner-medium": "urchade/gliner_medium-v2.1",
    "gliner-multi": "urchade/gliner_multi-v2.1",
    "nuner-zero": "numind/NuNER_Zero",
}


def fold_of(document_id: str) -> int:
    """
    Return the fold (0 or 1) of a document from its item index.

    :param document_id: Document id such as ``12h``.
    :type document_id: str
    :return: Fold number.
    :rtype: int
    """
    return int(re.match(r"\d+", document_id).group()) % 2


def build_candidate(name: str, vocabulary: dict, threshold: float, arguments):
    """
    Construct a candidate by name.

    :param name: Candidate name.
    :type name: str
    :param vocabulary: Closed vocabulary.
    :type vocabulary: dict
    :param threshold: Score threshold for zero-shot models.
    :type threshold: float
    :param arguments: Parsed command-line arguments.
    :return: Candidate instance.
    """
    empty = Registry([])
    if name == "gazetteer":
        return GazetteerCandidate(vocabulary, empty)
    if name == "spacy":
        return SpacyCandidate(vocabulary, empty)
    if name in GLINER_MODELS:
        return GlinerCandidate(vocabulary, empty, GLINER_MODELS[name], threshold, name)
    if name == "gliner2":
        return Gliner2Candidate(vocabulary, empty, threshold)
    if name == "relex":
        return RelexCandidate(vocabulary, empty, threshold)
    if name == "glirel":
        return GlirelCandidate(vocabulary, empty, threshold)
    if name == "hybrid":
        return HybridCandidate(vocabulary, empty, threshold)
    if name == "llm":
        return LlmCandidate(
            vocabulary,
            empty,
            "gpt-6-luna",
            arguments.budget_usd,
            arguments.price_in,
            arguments.price_out,
        )
    raise SystemExit(f"unknown candidate {name}")


def main() -> int:
    """
    Command-line entry point.

    :return: Process exit status.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--lab", type=Path, default=LAB_DIRECTORY)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--budget-usd", type=float, default=2.0)
    parser.add_argument("--price-in", type=float, default=0.0, help="USD per million input tokens")
    parser.add_argument(
        "--price-out", type=float, default=0.0, help="USD per million output tokens"
    )
    parser.add_argument("--tag", default="")
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="timed repetitions per document; the median is reported",
    )
    arguments = parser.parse_args()

    vocabulary = load_vocabulary(arguments.lab / "vocabulary.yml")
    documents = load_jsonl(arguments.lab / "documents.jsonl")
    gold = {record["id"]: record for record in load_jsonl(arguments.lab / "gold.jsonl")}
    if arguments.limit:
        documents = documents[: arguments.limit]

    started = time.perf_counter()
    candidate = build_candidate(arguments.candidate, vocabulary, arguments.threshold, arguments)
    load_seconds = time.perf_counter() - started
    registries = {
        fold: Registry([gold[d["id"]] for d in documents if fold_of(d["id"]) != fold])
        for fold in (0, 1)
    }

    for document in documents[:3]:
        candidate.registry = registries[fold_of(document["id"])]
        try:
            candidate.extract(document["text"])
        except RuntimeError:
            break

    label = arguments.candidate + (
        f"@{arguments.threshold}"
        if arguments.tag == "" and arguments.candidate not in ("gazetteer", "spacy", "llm")
        else ""
    )
    arguments.out.mkdir(parents=True, exist_ok=True)
    predictions_path = arguments.out / f"{label}.predictions.jsonl"
    errors = 0
    with predictions_path.open("w", encoding="utf-8") as handle:
        for document in documents:
            registry = registries[fold_of(document["id"])]
            candidate.registry = registry
            if hasattr(candidate, "span_model"):
                candidate.span_model.registry = registry
            error = None
            wall_samples, cpu_samples = [], []
            mentions, relations = [], []
            for repeat in range(arguments.repeats):
                begin, cpu_begin = time.perf_counter(), time.process_time()
                try:
                    found_mentions, found_relations = candidate.extract(document["text"])
                    if repeat == 0:
                        mentions, relations = found_mentions, found_relations
                except Exception as exception:
                    error = f"{type(exception).__name__}: {exception}"
                    errors += 1
                    break
                wall_samples.append((time.perf_counter() - begin) * 1000)
                cpu_samples.append((time.process_time() - cpu_begin) * 1000)
            latency_ms = statistics.median(wall_samples) if wall_samples else 0.0
            cpu_ms = statistics.median(cpu_samples) if cpu_samples else 0.0
            handle.write(
                json.dumps(
                    {
                        "id": document["id"],
                        "latency_ms": latency_ms,
                        "cpu_ms": cpu_ms,
                        "mentions": mentions,
                        "relations": relations,
                        "error": error,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    meta = {
        "candidate": label,
        "name": candidate.name,
        "version": candidate.version,
        "threshold": arguments.threshold,
        "load_seconds": load_seconds,
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024,
        "documents": len(documents),
        "errors": errors,
        "repeats": arguments.repeats,
        "machine_load_average_at_end": os.getloadavg()[0],
    }
    if arguments.candidate == "llm":
        meta.update(
            {
                "spent_usd": candidate.spent_usd,
                "tokens_in": candidate.tokens_in,
                "tokens_out": candidate.tokens_out,
            }
        )
    (arguments.out / f"{label}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
