"""
Fetch the WikiText-2 raw dataset into a local fixture directory.

This script is intentionally small and dependency-light from Biblicus's perspective.
It is used by CI to ensure a stable, cached corpus is available for behavior specs and
demo-like tests that need "real-ish" text at scale without checking large datasets into Git.
"""

from __future__ import annotations

from pathlib import Path


def _fixture_root() -> Path:
    """
    Resolve the repository-local fixture root directory.

    :return: Fixture root path.
    :rtype: Path
    """
    return Path(__file__).resolve().parent


def _wikitext2_output_dir() -> Path:
    """
    Resolve the output directory for the WikiText-2 raw fixture.

    :return: Output directory path.
    :rtype: Path
    """
    return _fixture_root() / "wikitext2_raw"


def _huggingface_cache_dir() -> Path:
    """
    Resolve a repository-local Hugging Face cache directory.

    :return: Cache directory path.
    :rtype: Path
    """
    return _fixture_root() / "cache" / "huggingface"


def _write_split_text(output_path: Path, rows: list[dict[str, object]]) -> None:
    """
    Write a dataset split to a text file.

    :param output_path: Output file path.
    :type output_path: Path
    :param rows: Dataset rows containing a ``text`` field.
    :type rows: list[dict[str, object]]
    :return: None.
    :rtype: None
    """
    lines: list[str] = []
    for row in rows:
        text_value = row.get("text", "")
        if not isinstance(text_value, str):
            continue
        lines.append(text_value)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fetch_wikitext2_raw() -> Path:
    """
    Fetch WikiText-2 raw and write it to ``tests/fixtures/wikitext2_raw``.

    The output format is three UTF-8 text files:

    - ``train.txt``
    - ``validation.txt``
    - ``test.txt``

    :return: Output directory where files were written.
    :rtype: Path
    :raises RuntimeError: If the ``datasets`` dependency is not installed.
    """
    output_dir = _wikitext2_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = output_dir / "train.txt"
    validation_path = output_dir / "validation.txt"
    test_path = output_dir / "test.txt"

    if train_path.is_file() and validation_path.is_file() and test_path.is_file():
        return output_dir

    try:
        from datasets import load_dataset  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency 'datasets'. Install with: pip install -e '.[datasets]'."
        ) from exc

    cache_dir = _huggingface_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(
        "wikitext",
        "wikitext-2-raw-v1",
        cache_dir=str(cache_dir),
    )

    _write_split_text(train_path, list(dataset["train"]))
    _write_split_text(validation_path, list(dataset["validation"]))
    _write_split_text(test_path, list(dataset["test"]))
    return output_dir


if __name__ == "__main__":
    output_dir = fetch_wikitext2_raw()
    print(f"WikiText-2 raw fixture available at: {output_dir}")
