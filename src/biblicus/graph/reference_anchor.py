"""
Reference anchor helpers for graph extraction.

Biblicus catalog items map to Papyrus ``Reference`` records at publish time.
Graph extraction uses a lightweight ``reference`` anchor node (not a
``SemanticNode``) only to attach ``mentions`` edges during export.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .models import GraphNode

if TYPE_CHECKING:
    from ..models import CatalogItem


def build_reference_anchor_node(item: CatalogItem) -> GraphNode:
    """
    Build a graph anchor for the corpus item that resolves to a Reference on import.

    :param item: Catalog item being extracted.
    :type item: CatalogItem
    :return: Reference anchor node.
    :rtype: GraphNode
    """
    return GraphNode(
        node_id=f"reference:{item.id}",
        node_type="reference",
        label=item.title or item.relpath,
        properties={
            "reference_id": item.id,
            "item_id": item.id,
        },
    )


def should_suppress_reference_title(label: str, blocked_forms: set[str]) -> bool:
    """
    Return whether an extracted entity label duplicates the reference title.

    :param label: Candidate entity surface form.
    :type label: str
    :param blocked_forms: Lowercase blocked surface forms from :func:`reference_title_blocked_forms`.
    :type blocked_forms: set[str]
    :return: True when the label should be suppressed.
    :rtype: bool
    """
    normalized = label.strip().lower()
    return bool(normalized and normalized in blocked_forms)


def reference_title_blocked_forms(item: CatalogItem) -> set[str]:
    """
    Surface forms for the reference title to suppress as duplicate NER entities.

    :param item: Catalog item being extracted.
    :type item: CatalogItem
    :return: Lowercase blocked surface forms.
    :rtype: set[str]
    """
    blocked: set[str] = set()
    for candidate in (item.title, item.relpath):
        if not isinstance(candidate, str):
            continue
        text = candidate.strip()
        if not text:
            continue
        blocked.add(text.lower())
        stem = re.sub(r"\.(pdf|html|txt|md)$", "", text, flags=re.IGNORECASE).strip()
        if stem:
            blocked.add(stem.lower())
    return blocked
