"""
Build a Biblicus corpus and an entity registry from the typed extraction lab, for running the typed-entity extractor.

The corpus holds one Markdown note per lab document and a pass-through text extraction snapshot. The registry is built from
the gold labels of every document whose item index is even; the other documents therefore mention both known and new
entities. The script also writes ``item-map.json``, mapping each lab document identifier to its corpus item identifier.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import LAB_DIRECTORY, load_jsonl  # noqa: E402

from biblicus.corpus import Corpus  # noqa: E402
from biblicus.extraction import build_extraction_snapshot  # noqa: E402


def build_registry(documents: List[dict], gold: Dict[str, dict]) -> List[dict]:
    """
    Build a registry from the gold mentions of every document with an even item index.

    :param documents: Lab documents in file order.
    :type documents: list[dict]
    :param gold: Gold records keyed by document identifier.
    :type gold: dict[str, dict]
    :return: Registry entries with ``key``, ``kind`` and ``aliases``.
    :rtype: list[dict]
    """
    entries: Dict[str, dict] = {}
    for document in documents:
        index = int(re.match(r"\d+", document["id"]).group())
        if index % 2:
            continue
        for mention in gold[document["id"]]["mentions"]:
            entry = entries.setdefault(
                mention["key"], {"key": mention["key"], "kind": mention["kind"], "aliases": set()}
            )
            entry["aliases"].add(mention["text"])
    return [
        {"key": key, "kind": entry["kind"], "aliases": sorted(entry["aliases"])}
        for key, entry in sorted(entries.items())
    ]


def main() -> None:
    """
    Create the corpus, the extraction snapshot, the registry and the item map.

    :return: None.
    :rtype: None
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Empty directory to create.")
    arguments = parser.parse_args()
    documents = load_jsonl(LAB_DIRECTORY / "documents.jsonl")
    gold = {record["id"]: record for record in load_jsonl(LAB_DIRECTORY / "gold.jsonl")}
    arguments.out.mkdir(parents=True, exist_ok=False)
    corpus = Corpus.init(arguments.out / "corpus")
    item_map = {}
    for document in documents:
        result = corpus.ingest_note(document["text"], title=document["id"])
        item_map[document["id"]] = result.item_id
    build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="lab",
        configuration={"stages": [{"extractor_id": "pass-through-text", "config": {}}]},
    )
    (arguments.out / "item-map.json").write_text(json.dumps(item_map, indent=2), encoding="utf-8")
    (arguments.out / "registry.json").write_text(
        json.dumps(build_registry(documents, gold), indent=2), encoding="utf-8"
    )
    print(f"corpus: {arguments.out / 'corpus'}")
    print(f"documents: {len(documents)}")


if __name__ == "__main__":
    main()
