from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from behave import then, when

from biblicus.corpus import Corpus
from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _catalog_source_uris(corpus_root: Path) -> list[str]:
    corpus = Corpus.open(corpus_root)
    catalog = corpus.load_catalog()
    return [str(item.source_uri or "") for item in catalog.items.values()]


@when(
    'I crawl the hypertext transfer protocol uniform resource locator "{filename}" with allowed prefix "{prefix}" into corpus "{corpus_name}"'
)
def step_crawl_http(context, filename: str, prefix: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    base = getattr(context, "http_base_url", None)
    assert isinstance(base, str) and base
    root_url = base + quote(filename)
    allowed_prefix = base + quote(prefix)
    args = [
        "--corpus",
        str(corpus),
        "crawl",
        "--root-url",
        root_url,
        "--allowed-prefix",
        allowed_prefix,
        "--max-items",
        "50",
        "--tags",
        "crawled",
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_crawl = json.loads(result.stdout)


@then("the crawl reports {key} {value:d}")
def step_crawl_reports_key_value(context, key: str, value: int) -> None:
    data = getattr(context, "last_crawl", None)
    assert isinstance(data, dict)
    assert int(data.get(key, -1)) == value


@then(
    'the corpus contains a crawled item with source uniform resource identifier ending with "{suffix}"'
)
def step_corpus_contains_crawled_item_source_uri_suffix(context, suffix: str) -> None:
    corpus_root = _corpus_path(context, "corpus")
    source_uris = _catalog_source_uris(corpus_root)
    assert any(uri.endswith(suffix) for uri in source_uris), source_uris


@then(
    'the corpus does not contain a crawled item with source uniform resource identifier ending with "{suffix}"'
)
def step_corpus_does_not_contain_crawled_item_source_uri_suffix(context, suffix: str) -> None:
    corpus_root = _corpus_path(context, "corpus")
    source_uris = _catalog_source_uris(corpus_root)
    assert all(not uri.endswith(suffix) for uri in source_uris), source_uris
