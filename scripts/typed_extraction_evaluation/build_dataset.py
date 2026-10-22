"""
Build the typed extraction evaluation documents and gold labels from a published-item export.

The export is a DynamoDB scan of the Shipped ``PublishedItem`` table. Every published item
yields two documents: the headline plus deck, and the first body paragraph. Gold labels are
written in a compact annotation file (see ``datasets/typed_extraction_lab/annotation_guide.md``)
and converted here to character-offset spans, with every surface form checked against the text.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import LAB_DIRECTORY, load_vocabulary, normalise_name  # noqa: E402


def unwrap_attribute(value):
    """
    Convert a DynamoDB attribute value into plain Python data.

    :param value: DynamoDB attribute dictionary.
    :type value: dict
    :return: Plain Python value.
    :rtype: object
    """
    if "S" in value:
        return value["S"]
    if "N" in value:
        return value["N"]
    if "L" in value:
        return [unwrap_attribute(item) for item in value["L"]]
    if "M" in value:
        return {key: unwrap_attribute(item) for key, item in value["M"].items()}
    if "BOOL" in value:
        return value["BOOL"]
    return None


def build_documents(scan_path: Path) -> List[dict]:
    """
    Turn a DynamoDB scan into evaluation documents.

    :param scan_path: Path of the ``aws dynamodb scan`` JSON output.
    :type scan_path: pathlib.Path
    :return: Documents with id, item id, slug, part and text, ordered by slug.
    :rtype: list[dict]
    """
    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    items = [
        {key: unwrap_attribute(value) for key, value in raw.items() if key != "bodyIr"}
        for raw in scan["Items"]
    ]
    items.sort(key=lambda item: item["slug"])
    documents = []
    for index, item in enumerate(items):
        body = item["bodyMarkus"].split("\n## ")[0]
        paragraphs = [part.strip() for part in body.split("\n\n") if part.strip()]
        front = yaml.safe_load(item["metadata"]["frontMatterYaml"])
        head_text = item["title"] + "\n" + (item.get("deck") or "")
        for part, text in (("h", head_text), ("b", paragraphs[0])):
            documents.append(
                {
                    "id": f"{index}{part}",
                    "item_id": item["id"],
                    "slug": item["slug"],
                    "part": "headline_deck" if part == "h" else "first_paragraph",
                    "text": text,
                    "front_matter_entities": front.get("entities") or [],
                    "front_matter_maker": front.get("maker"),
                }
            )
    return documents


def parse_annotations(path: Path) -> Dict[str, dict]:
    """
    Parse the compact annotation file.

    :param path: Annotation file path.
    :type path: pathlib.Path
    :return: Mapping from document id to ``{"mentions": [(kind, surface, key)], "relations": [(s, r, o)]}``.
    :rtype: dict[str, dict]
    """
    annotations: Dict[str, dict] = {}
    current = None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        if line.startswith("## "):
            current = annotations.setdefault(line[3:].strip(), {"mentions": [], "relations": []})
            continue
        label, _, rest = line.partition(":")
        label = label.strip()
        if label == "rel":
            subject, relation, obj = [part.strip() for part in rest.split("|")]
            current["relations"].append((subject, relation, obj))
            continue
        for chunk in rest.split(" ; "):
            chunk = chunk.strip()
            surface, _, key = chunk.partition("=")
            current["mentions"].append((label, surface.strip(), (key or surface).strip()))
    return annotations


def find_spans(text: str, surface: str) -> List[Tuple[int, int]]:
    """
    Find every whole-token occurrence of a surface form.

    :param text: Document text.
    :type text: str
    :param surface: Surface form.
    :type surface: str
    :return: Start and end character offsets.
    :rtype: list[tuple[int, int]]
    """
    pattern = r"(?<![0-9A-Za-z])" + re.escape(surface) + r"(?![0-9A-Za-z])"
    return [(match.start(), match.end()) for match in re.finditer(pattern, text)]


def build_gold(
    documents: List[dict], annotations: Dict[str, dict], vocabulary: Dict[str, List[str]]
):
    """
    Convert annotations into span-level gold labels and report every inconsistency.

    :param documents: Evaluation documents.
    :type documents: list[dict]
    :param annotations: Parsed annotations.
    :type annotations: dict
    :param vocabulary: Closed vocabulary.
    :type vocabulary: dict
    :return: Gold records and a list of error messages.
    :rtype: tuple[list[dict], list[str]]
    """
    errors: List[str] = []
    gold = []
    by_id = {document["id"]: document for document in documents}
    for document_id in by_id:
        if document_id not in annotations:
            errors.append(f"{document_id}: no annotation block")
    for document_id, annotation in annotations.items():
        if document_id not in by_id:
            errors.append(f"{document_id}: unknown document")
            continue
        text = by_id[document_id]["text"]
        claimed: List[Tuple[int, int]] = []
        mentions = []
        for kind, surface, key in sorted(annotation["mentions"], key=lambda entry: -len(entry[1])):
            if kind not in vocabulary["entity_kinds"]:
                errors.append(f"{document_id}: kind {kind!r} not in vocabulary")
                continue
            spans = find_spans(text, surface)
            if not spans:
                errors.append(f"{document_id}: surface {surface!r} not found")
                continue
            for start, end in spans:
                if any(start < c_end and c_start < end for c_start, c_end in claimed):
                    continue
                claimed.append((start, end))
                mentions.append(
                    {
                        "kind": kind,
                        "start": start,
                        "end": end,
                        "text": text[start:end],
                        "key": normalise_name(key),
                    }
                )
        mentions.sort(key=lambda mention: mention["start"])
        known_keys = {mention["key"] for mention in mentions} | {
            normalise_name(mention["text"]) for mention in mentions
        }
        relations = []
        for subject, relation, obj in annotation["relations"]:
            if relation not in vocabulary["relation_types"]:
                errors.append(f"{document_id}: relation {relation!r} not in vocabulary")
                continue
            for endpoint in (subject, obj):
                if normalise_name(endpoint) not in known_keys:
                    errors.append(f"{document_id}: relation endpoint {endpoint!r} has no mention")
            relations.append(
                {
                    "subject": normalise_name(subject),
                    "type": relation,
                    "object": normalise_name(obj),
                }
            )
        gold.append({"id": document_id, "mentions": mentions, "relations": relations})
    gold.sort(key=lambda record: (int(re.match(r"\d+", record["id"]).group()), record["id"][-1]))
    return gold, errors


def main() -> int:
    """
    Command-line entry point.

    :return: Process exit status.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan-json", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, default=LAB_DIRECTORY)
    arguments = parser.parse_args()
    documents = build_documents(arguments.scan_json)
    annotations: Dict[str, dict] = {}
    for path in arguments.annotations:
        annotations.update(parse_annotations(path))
    gold, errors = build_gold(documents, annotations, load_vocabulary())
    if errors:
        print("\n".join(errors))
        return 1
    arguments.out.mkdir(parents=True, exist_ok=True)
    public_documents = [
        {key: document[key] for key in ("id", "item_id", "slug", "part", "text")}
        for document in documents
    ]
    (arguments.out / "documents.jsonl").write_text(
        "".join(json.dumps(document, ensure_ascii=False) + "\n" for document in public_documents),
        encoding="utf-8",
    )
    (arguments.out / "gold.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in gold), encoding="utf-8"
    )
    print(
        f"{len(documents)} documents, {sum(len(r['mentions']) for r in gold)} mentions, {sum(len(r['relations']) for r in gold)} relations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
