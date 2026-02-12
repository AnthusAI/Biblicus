from __future__ import annotations

from pathlib import Path

from behave import given


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


def _resolve_fixture_path(context, filename: str) -> Path:
    """Resolve fixture path, accounting for corpus root if set."""
    candidate = Path(filename)
    if candidate.is_absolute():
        return candidate
    workdir_path = (context.workdir / candidate).resolve()
    if candidate.parts and candidate.parts[0] == ".biblicus":
        return workdir_path
    corpus_root = getattr(context, "last_corpus_root", None)
    if corpus_root is not None:
        if candidate.parts and candidate.parts[0] == corpus_root.name:
            return workdir_path
        return (corpus_root / candidate).resolve()
    return workdir_path


@given(
    'a WikiText-2 raw sample file "{filename}" exists with split "{split}" and first {lines:d} lines'
)
def step_create_wikitext_sample_file(context, filename: str, split: str, lines: int) -> None:
    source_path = _fixture_split_path(split)
    if not source_path.is_file():
        raise AssertionError(
            "WikiText-2 raw fixture is missing. Run: python tests/fixtures/fetch_wikitext2.py"
        )
    raw_lines = source_path.read_text(encoding="utf-8").splitlines()
    sample = "\n".join(raw_lines[:lines]) + "\n"
    path = _resolve_fixture_path(context, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sample, encoding="utf-8")
