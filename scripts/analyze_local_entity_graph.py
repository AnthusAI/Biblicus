#!/usr/bin/env python3
"""Summarize a local ner-entities graph export for quality review."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def _load_export(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _entity_nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = payload.get("nodes") or []
    return [n for n in nodes if str(n.get("node_type") or "") == "entity"]


def _person_like(label: str) -> bool:
    if not label or len(label) > 80:
        return False
    if re.search(r"\d", label):
        return False
    parts = label.split()
    if len(parts) == 1:
        return bool(re.match(r"^[A-Z][a-z'\-]+$", parts[0]))
    if 1 < len(parts) <= 4:
        return all(re.match(r"^[A-Z][A-Za-z'\-]+$", p) for p in parts)
    return False


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    entities = _entity_nodes(payload)
    edges = payload.get("edges") or []
    by_type = Counter(
        str((n.get("properties") or {}).get("entity_type") or "UNKNOWN") for n in entities
    )
    mention_edges = [e for e in edges if str(e.get("edge_type") or "") == "mentions"]
    relation_edges = [e for e in edges if str(e.get("edge_type") or "") == "related_to"]
    labels = [str(n.get("label") or "") for n in entities]
    person_like = [label for label in labels if _person_like(label)]
    top = Counter(labels).most_common(30)
    per_labels = [
        str(n.get("label") or "")
        for n in entities
        if str((n.get("properties") or {}).get("entity_type") or "") == "PER"
    ]
    return {
        "entity_count": len(entities),
        "mention_edge_count": len(mention_edges),
        "related_to_edge_count": len(relation_edges),
        "entity_types": dict(by_type.most_common()),
        "person_like_count": len(person_like),
        "person_like_fraction": round(len(person_like) / max(len(entities), 1), 4),
        "per_entity_count": len(per_labels),
        "top_entities": top,
        "sample_per": sorted(set(per_labels))[:40],
        "sample_person_like": sorted(set(person_like))[:40],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_json", type=Path, help="Path to graph export JSON")
    parser.add_argument("--output", type=Path, default=None, help="Write summary JSON here")
    args = parser.parse_args()
    summary = analyze(_load_export(args.export_json))
    text = json.dumps(summary, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
