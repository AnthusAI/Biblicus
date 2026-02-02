from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List

from biblicus.context import ContextPack, ContextPackBlock
from biblicus.context_engine import ContextRetrieverRequest


def _fixture_split_path(split: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    fixture_dir = repo_root / "tests" / "fixtures" / "wikitext2_raw"
    if split == "train":
        return fixture_dir / "train.txt"
    if split == "validation":
        return fixture_dir / "validation.txt"
    if split == "test":
        return fixture_dir / "test.txt"
    raise ValueError(f"Unknown wikitext split: {split!r}")


def load_wikitext_texts(split: str, limit: int | None = None) -> List[str]:
    source_path = _fixture_split_path(split)
    if not source_path.is_file():
        raise AssertionError(
            "WikiText-2 raw fixture is missing. Run: python tests/fixtures/fetch_wikitext2.py"
        )
    texts = [line for line in source_path.read_text(encoding="utf-8").splitlines() if line]
    if limit is not None:
        return texts[:limit]
    return texts


def ensure_wikitext2_raw() -> None:
    for split in ("train", "validation", "test"):
        source_path = _fixture_split_path(split)
        if not source_path.is_file():
            raise AssertionError(
                "WikiText-2 raw fixture is missing. Run: python tests/fixtures/fetch_wikitext2.py"
            )


def retrieve_wikitext2(request: ContextRetrieverRequest) -> ContextPack:
    split = request.metadata.get("split", "train")
    maximum_cache_total_items = request.metadata.get("maximum_cache_total_items")
    maximum_cache_total_characters = request.metadata.get("maximum_cache_total_characters")
    texts = load_wikitext_texts(split, limit=None)
    if maximum_cache_total_items is not None:
        texts = texts[: int(maximum_cache_total_items)]
    elif maximum_cache_total_characters is not None:
        selected = []
        total_chars = 0
        for text in texts:
            text_length = len(text)
            if total_chars + text_length > int(maximum_cache_total_characters):
                break
            selected.append(text)
            total_chars += text_length
        texts = selected
    ranked = _rank_texts(request.query, texts)
    offset = request.offset
    limit = request.limit
    selected = ranked[offset : offset + limit]

    blocks: list[ContextPackBlock] = []
    remaining_chars = request.maximum_total_characters
    for idx, text in enumerate(selected, start=1):
        snippet = text.strip()
        if remaining_chars is not None and remaining_chars <= 0:
            break
        if remaining_chars is not None and len(snippet) > remaining_chars:
            snippet = snippet[: remaining_chars - 3].rstrip() + "..."
        if remaining_chars is not None:
            remaining_chars -= len(snippet)
        if not snippet:
            continue
        blocks.append(
            ContextPackBlock(
                evidence_item_id=f"{split}-{offset + idx}",
                text=snippet,
                metadata=None,
            )
        )

    text = "\n\n".join(block.text for block in blocks)
    return ContextPack(text=text, evidence_count=len(blocks), blocks=blocks)


def _rank_texts(query: str, texts: Iterable[str]) -> List[str]:
    query_terms = _tokenize(query)
    if not query_terms:
        return list(texts)
    scored = []
    for text in texts:
        text_terms = _tokenize(text)
        score = sum(text_terms.count(term) for term in query_terms)
        scored.append((score, text))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [text for score, text in scored if score > 0] or list(texts)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())
