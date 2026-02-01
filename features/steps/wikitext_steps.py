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
    (context.workdir / filename).write_text(sample, encoding="utf-8")
