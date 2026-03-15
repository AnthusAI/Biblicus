from pathlib import Path

from biblicus import sources


def test_load_source_sniff_fallback(tmp_path):
    blob = tmp_path / "data.bin"
    blob.write_bytes(b"\x00\x01\x02")
    payload = sources.load_source(blob)
    assert payload.filename == "data.bin"
    assert payload.media_type == "application/octet-stream"
