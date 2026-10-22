"""
Score candidate predictions against the gold labels and write a summary JSON and Markdown tables.
"""

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidates import Registry  # noqa: E402
from common import LAB_DIRECTORY, load_jsonl, load_vocabulary, normalise_name  # noqa: E402

TRIM = " \t\n.,;:()\"'"


def fold_of(document_id: str) -> int:
    """
    Return the fold of a document id.

    :param document_id: Document id.
    :type document_id: str
    :return: 0 or 1.
    :rtype: int
    """
    return int(re.match(r"\d+", document_id).group()) % 2


def trimmed(text: str, start: int, end: int) -> Tuple[int, int]:
    """
    Trim surrounding punctuation and whitespace from a span.

    :param text: Document text.
    :type text: str
    :param start: Span start.
    :type start: int
    :param end: Span end.
    :type end: int
    :return: Trimmed start and end.
    :rtype: tuple[int, int]
    """
    while start < end and text[start] in TRIM:
        start += 1
    while end > start and text[end - 1] in TRIM:
        end -= 1
    return start, end


def overlap_ratio(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    """
    Intersection over union of two spans.

    :param a: First span.
    :type a: tuple[int, int]
    :param b: Second span.
    :type b: tuple[int, int]
    :return: Intersection over union.
    :rtype: float
    """
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union else 0.0


def match_mentions(
    gold: List[dict], predicted: List[dict], texts_span, mode: str, typed: bool
) -> List[Tuple[int, int]]:
    """
    Greedy one-to-one matching of predicted to gold mentions.

    :param gold: Gold mentions.
    :type gold: list[dict]
    :param predicted: Predicted mentions.
    :type predicted: list[dict]
    :param texts_span: Function mapping a mention to its trimmed span.
    :type texts_span: callable
    :param mode: ``strict`` (exact span) or ``lenient`` (intersection over union of at least 0.5).
    :type mode: str
    :param typed: Whether the kind must also match.
    :type typed: bool
    :return: Matched ``(gold index, predicted index)`` pairs.
    :rtype: list[tuple[int, int]]
    """
    pairs = []
    for gi, g in enumerate(gold):
        for pi, p in enumerate(predicted):
            if p["start"] is None or p["start"] < 0:
                continue
            if typed and g["kind"] != p["kind"]:
                continue
            ratio = overlap_ratio(texts_span(g), texts_span(p))
            if (mode == "strict" and ratio == 1.0) or (mode == "lenient" and ratio >= 0.5):
                pairs.append((ratio, gi, pi))
    pairs.sort(key=lambda entry: -entry[0])
    used_g, used_p, matched = set(), set(), []
    for _, gi, pi in pairs:
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        matched.append((gi, pi))
    return matched


def prf(tp: int, fp: int, fn: int) -> Dict[str, float]:
    """
    Precision, recall and F1 with support.

    :param tp: True positives.
    :type tp: int
    :param fp: False positives.
    :type fp: int
    :param fn: False negatives.
    :type fn: int
    :return: Metrics dictionary.
    :rtype: dict[str, float]
    """
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "support": tp + fn,
    }


def percentile(values: List[float], q: float) -> float:
    """
    Linear-interpolation percentile.

    :param values: Sample.
    :type values: list[float]
    :param q: Quantile between 0 and 1.
    :type q: float
    :return: Percentile value.
    :rtype: float
    """
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low, high = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def score_candidate(label: str, results: Path, lab: Path, vocabulary: dict) -> dict:
    """
    Compute every metric for one candidate.

    :param label: Candidate label (file stem).
    :type label: str
    :param results: Results directory.
    :type results: pathlib.Path
    :param lab: Evaluation set directory.
    :type lab: pathlib.Path
    :param vocabulary: Closed vocabulary.
    :type vocabulary: dict
    :return: Summary dictionary.
    :rtype: dict
    """
    documents = {d["id"]: d for d in load_jsonl(lab / "documents.jsonl")}
    gold = {g["id"]: g for g in load_jsonl(lab / "gold.jsonl")}
    predictions = {p["id"]: p for p in load_jsonl(results / f"{label}.predictions.jsonl")}
    meta = json.loads((results / f"{label}.meta.json").read_text())
    kinds, relation_types = vocabulary["entity_kinds"], vocabulary["relation_types"]

    counts = {
        mode: {"typed": {k: [0, 0, 0] for k in kinds}, "untyped": [0, 0, 0]}
        for mode in ("strict", "lenient")
    }
    relation_counts = {t: [0, 0, 0] for t in relation_types}
    resolution = Counter()
    spurious, wrong_kind, ungrounded = Counter(), Counter(), Counter()
    spurious_total = wrong_kind_total = ungrounded_total = predicted_total = 0
    hallucinated_relation_endpoints = 0
    relation_total = 0
    registry_keys = {0: defaultdict(set), 1: defaultdict(set)}
    for document_id, record in gold.items():
        for mention in record["mentions"]:
            registry_keys[1 - fold_of(document_id)][mention["kind"]].add(mention["key"])
    registries = {
        fold: Registry([r for i, r in gold.items() if fold_of(i) != fold]) for fold in (0, 1)
    }

    for document_id, g in gold.items():
        text = documents[document_id]["text"]
        prediction = predictions[document_id]
        gm, pm = g["mentions"], prediction["mentions"]
        for mention in pm:
            key = registries[fold_of(document_id)].resolve(mention["text"], mention["kind"])
            mention["state"] = "resolved" if key else "proposed"
            mention["entity_key"] = key

        def span(m):
            return trimmed(text, m["start"], m["end"])

        for mode in ("strict", "lenient"):
            typed_pairs = match_mentions(gm, pm, span, mode, True)
            for kind in kinds:
                gk = [i for i, m in enumerate(gm) if m["kind"] == kind]
                pk = [
                    i
                    for i, m in enumerate(pm)
                    if m["kind"] == kind and m["start"] is not None and m["start"] >= 0
                ]
                tp = sum(1 for gi, pi in typed_pairs if gm[gi]["kind"] == kind)
                counts[mode]["typed"][kind][0] += tp
                counts[mode]["typed"][kind][1] += len(pk) - tp
                counts[mode]["typed"][kind][2] += len(gk) - tp
            untyped_pairs = match_mentions(gm, pm, span, mode, False)
            valid_predictions = sum(1 for m in pm if m["start"] is not None and m["start"] >= 0)
            counts[mode]["untyped"][0] += len(untyped_pairs)
            counts[mode]["untyped"][1] += valid_predictions - len(untyped_pairs)
            counts[mode]["untyped"][2] += len(gm) - len(untyped_pairs)

        typed_lenient = {pi: gi for gi, pi in match_mentions(gm, pm, span, "lenient", True)}
        for pi, p in enumerate(pm):
            predicted_total += 1
            if p["start"] is None or p["start"] < 0:
                ungrounded_total += 1
                ungrounded[p["text"]] += 1
                continue
            if pi in typed_lenient:
                gi = typed_lenient[pi]
                known = gm[gi]["key"] in registry_keys[fold_of(document_id)][gm[gi]["kind"]]
                if known:
                    if p.get("entity_key") == gm[gi]["key"]:
                        resolution["known_resolved_correctly"] += 1
                    elif p.get("state") == "resolved":
                        resolution["known_resolved_to_wrong_entity"] += 1
                    else:
                        resolution["known_left_unresolved"] += 1
                else:
                    resolution[
                        "new_proposed" if p.get("state") == "proposed" else "new_wrongly_merged"
                    ] += 1
                continue
            overlapping = [m for m in gm if overlap_ratio(span(m), span(p)) > 0]
            if overlapping:
                wrong_kind_total += 1
                wrong_kind[f"{p['text']} ({p['kind']} vs {overlapping[0]['kind']})"] += 1
            else:
                spurious_total += 1
                spurious[f"{p['text']} ({p['kind']})"] += 1

        canon: Dict[str, str] = {}
        for m in gm:
            canon[normalise_name(m["text"])] = m["key"]
            canon[m["key"]] = m["key"]
        gold_triples = {
            (canon.get(r["subject"], r["subject"]), r["type"], canon.get(r["object"], r["object"]))
            for r in g["relations"]
        }
        predicted_triples = set()
        for r in prediction["relations"]:
            relation_total += 1
            subject, obj = normalise_name(r["subject"]["text"]), normalise_name(r["object"]["text"])
            if not endpoint_in(text_norm_cache(text), subject) or not endpoint_in(
                text_norm_cache(text), obj
            ):
                hallucinated_relation_endpoints += 1
            predicted_triples.add((canon.get(subject, subject), r["type"], canon.get(obj, obj)))
        for relation_type in relation_types:
            gt = {t for t in gold_triples if t[1] == relation_type}
            pt = {t for t in predicted_triples if t[1] == relation_type}
            relation_counts[relation_type][0] += len(gt & pt)
            relation_counts[relation_type][1] += len(pt - gt)
            relation_counts[relation_type][2] += len(gt - pt)

    def summarise(table):
        per = {k: prf(*v) for k, v in table.items()}
        total = prf(*[sum(v[i] for v in table.values()) for i in range(3)])
        supported = [m for m in per.values() if m["support"] > 0]
        macro = sum(m["f1"] for m in supported) / len(supported) if supported else 0.0
        return per, total, macro

    entity_summary = {}
    for mode in ("strict", "lenient"):
        per, total, macro = summarise(counts[mode]["typed"])
        entity_summary[mode] = {
            "per_kind": per,
            "micro": total,
            "macro_f1": macro,
            "untyped": prf(*counts[mode]["untyped"]),
        }
    per_relation, relation_micro, relation_macro = summarise(relation_counts)
    latencies = [predictions[i]["latency_ms"] for i in gold]
    cpu_times = [predictions[i].get("cpu_ms", 0.0) for i in gold]
    documents_count = len(gold)
    cost = (meta.get("spent_usd", 0.0) / documents_count * 1000) if "spent_usd" in meta else 0.0
    return {
        "label": label,
        "meta": meta,
        "entities": entity_summary,
        "relations": {
            "per_type": per_relation,
            "micro": relation_micro,
            "macro_f1": relation_macro,
        },
        "latency_ms": {
            "median": statistics.median(latencies),
            "p95": percentile(latencies, 0.95),
            "mean": statistics.mean(latencies),
        },
        "cpu_ms": {
            "median": statistics.median(cpu_times),
            "p95": percentile(cpu_times, 0.95),
            "mean": statistics.mean(cpu_times),
        },
        "cpu_seconds_per_1000_documents": statistics.mean(cpu_times),
        "api_cost_usd_per_1000_documents": cost,
        "resolution": dict(resolution),
        "failure_modes": {
            "predicted_mentions": predicted_total,
            "spurious_no_gold_overlap": spurious_total,
            "wrong_kind_overlap": wrong_kind_total,
            "ungrounded_text_not_in_source": ungrounded_total,
            "relation_endpoints_not_in_source": hallucinated_relation_endpoints,
            "relations_predicted": relation_total,
            "top_spurious": spurious.most_common(8),
            "top_wrong_kind": wrong_kind.most_common(6),
            "top_ungrounded": ungrounded.most_common(5),
        },
        "errors": meta.get("errors", 0),
    }


_NORM_CACHE: Dict[str, str] = {}


def text_norm_cache(text: str) -> str:
    """
    Normalised text padded for substring tests (cached).

    :param text: Document text.
    :type text: str
    :return: Normalised text.
    :rtype: str
    """
    if text not in _NORM_CACHE:
        _NORM_CACHE[text] = " " + normalise_name(text) + " "
    return _NORM_CACHE[text]


def endpoint_in(text_norm: str, endpoint: str) -> bool:
    """
    Test whether a normalised endpoint occurs in normalised text on token boundaries.

    :param text_norm: Normalised text padded with spaces.
    :type text_norm: str
    :param endpoint: Normalised endpoint.
    :type endpoint: str
    :return: Whether the endpoint occurs.
    :rtype: bool
    """
    return f" {endpoint} " in text_norm


def main() -> int:
    """
    Command-line entry point.

    :return: Process exit status.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--lab", type=Path, default=LAB_DIRECTORY)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    vocabulary = load_vocabulary(arguments.lab / "vocabulary.yml")
    labels = sorted(
        path.name[: -len(".meta.json")] for path in arguments.results.glob("*.meta.json")
    )
    summaries = [
        score_candidate(label, arguments.results, arguments.lab, vocabulary) for label in labels
    ]
    arguments.out.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"scored {len(summaries)} candidates -> {arguments.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
