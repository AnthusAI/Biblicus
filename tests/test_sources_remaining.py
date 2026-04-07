
import pytest

from biblicus.sources import load_source


def test_load_source_rejects_non_local_file_host(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("data")
    uri = f"file://example.com{target}"
    with pytest.raises(ValueError):
        load_source(uri)


def test_load_source_rejects_directory_without_index(tmp_path):
    directory = tmp_path / "folder"
    directory.mkdir()
    uri = directory.as_uri()
    with pytest.raises(IsADirectoryError):
        load_source(uri)


def test_load_source_rejects_unsupported_scheme():
    with pytest.raises(NotImplementedError):
        load_source("ftp://example.com/file.txt")


def test_load_source_uses_index_html(tmp_path):
    folder = tmp_path / "site"
    folder.mkdir()
    index = folder / "index.html"
    index.write_text("<html></html>", encoding="utf-8")
    payload = load_source(folder.as_uri())
    assert payload.filename.endswith("index.html")
    assert payload.media_type == "text/html"


def test_load_source_sniffs_media_type_and_adds_extension(tmp_path):
    blob = tmp_path / "blob"
    blob.write_bytes(b"OggS\x00\x02...binary...")
    payload = load_source(blob)
    assert payload.media_type == "audio/ogg"
    assert payload.filename.endswith(".ogg")
