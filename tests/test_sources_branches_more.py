import pytest

from biblicus import sources


def test_load_source_rejects_remote_file_host():
    with pytest.raises(ValueError):
        sources.load_source("file://example.com/path/to/file.txt")
