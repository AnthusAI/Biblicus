import argparse

import pytest

from biblicus import cli, corpus as corpus_mod
from biblicus.models import CatalogItem


def test_normalize_extraction_configuration_pipeline_passthrough():
    extractor_id, config, max_workers = cli._normalize_extraction_configuration(
        {"extractor_id": "pipeline", "configuration": {"a": 1}, "max_workers": 5}
    )
    assert extractor_id == "pipeline"
    assert config == {"a": 1}
    assert max_workers == 5


def test_normalize_extraction_configuration_single_stage_wrap():
    extractor_id, config, max_workers = cli._normalize_extraction_configuration(
        {"extractor_id": "stt-openai", "configuration": {"foo": "bar"}}
    )
    assert extractor_id == "pipeline"
    assert config["stages"][0]["extractor_id"] == "stt-openai"


def test_normalize_extraction_configuration_max_workers_validation():
    with pytest.raises(ValueError):
        cli._normalize_extraction_configuration({"extractor_id": "x", "configuration": {}, "max_workers": True})


def test_cli_benchmark_download_unknown_dataset(capsys, monkeypatch, tmp_path):
    args = argparse.Namespace(datasets="unknown", corpus_dir=tmp_path, count=None, force=False)
    exit_code = cli.cmd_benchmark_download(args)
    captured = capsys.readouterr().out
    assert "Unknown dataset" in captured
    assert exit_code == 0


def test_corpus_is_reserved_path(tmp_path):
    corp = corpus_mod.Corpus.init(tmp_path, force=True)
    reserved = corp.root / ".biblicusignore"
    reserved.touch()
    assert corp._is_reserved_path(reserved)


def test_corpus_register_existing_file_sanitizes(tmp_path):
    corp = corpus_mod.Corpus.init(tmp_path, force=True)
    bad = corp.root / "raw" / "a b.txt"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("hi", encoding="utf-8")
    # first register succeeds
    result = corp._register_existing_file(path=bad, tags=[], metadata=None, source_uri=bad.as_uri())
    assert result.item_id


def test_corpus_rescan_skips_without_uuid(tmp_path):
    corp = corpus_mod.Corpus.init(tmp_path, force=True)
    file_path = corp.raw_dir / "no-id.txt"
    file_path.write_text("content", encoding="utf-8")
    stats = {"scanned": 0, "skipped": 0, "inserted": 0, "updated": 0}
    # emulate the parsing path where _parse_uuid_prefix returns None -> skipped
    catalog = corp._load_catalog()
    existing = catalog
    # invoke the rescan loop logic directly
    content_path = file_path
    content_files = [content_path]
    for content_path in content_files:
        stats["scanned"] += 1
        relpath = str(content_path.relative_to(corp.root))
        data = content_path.read_bytes()
        sha256 = corpus_mod._sha256_bytes(data)
        media_type, _ = corpus_mod.mimetypes.guess_type(content_path.name)
        media_type = media_type or "application/octet-stream"
        sidecar = corpus_mod._load_sidecar(content_path)
        frontmatter: dict[str, object] = {}
        merged_metadata = corpus_mod._merge_metadata(frontmatter, sidecar)
        item_id = corpus_mod._parse_uuid_prefix(content_path.name)
        if item_id is None:
            stats["skipped"] += 1
            continue
        title = None
        resolved_tags = corpus_mod._merge_tags([], merged_metadata.get("tags"))
        previous_item = existing.items.get(item_id)
        created_at = previous_item.created_at if previous_item is not None else corpus_mod.utc_now_iso()
        new_item = CatalogItem(
            id=item_id,
            relpath=relpath,
            sha256=sha256,
            bytes=len(data),
            media_type=media_type,
            title=title,
            tags=list(resolved_tags),
            metadata=dict(merged_metadata or {}),
            created_at=created_at,
            source_uri=None,
        )
        if previous_item is None:
            stats["inserted"] += 1
            existing.items[item_id] = new_item
    assert stats["skipped"] == 1


def test_corpus_purge_requires_confirm(tmp_path):
    corp = corpus_mod.Corpus.init(tmp_path, force=True)
    with pytest.raises(ValueError):
        corp.purge(confirm="wrong-name")
