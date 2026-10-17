import json
from pathlib import Path

import pytest
import yaml

from biblicus import cli


def test_load_ingest_metadata_file_requires_mapping(tmp_path: Path):
    """
    Metadata files must parse to a mapping.
    """
    metadata_path = tmp_path / "metadata.yml"
    metadata_path.write_text("- a\n- b\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mapping/object"):
        cli._load_ingest_metadata_file(metadata_path)


def test_ingest_metadata_cli_uses_standard_item_storage(tmp_path: Path, capsys):
    """
    CLI metadata ingest writes canonical sidecar and catalog fields.
    """
    corpus_path = tmp_path / "corpus"
    source_path = tmp_path / "paper.pdf"
    metadata_path = tmp_path / "paper.metadata.yml"
    source_path.write_bytes(b"%PDF-1.4\n")
    metadata_path.write_text(
        yaml.safe_dump(
            {
                "title": "Curated Paper",
                "abstract": "A curated abstract.",
                "tags": ["metadata-tag"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assert cli.main(["init", str(corpus_path)]) == 0
    assert (
        cli.main(
            [
                "--corpus",
                str(corpus_path),
                "ingest",
                str(source_path),
                "--metadata-file",
                str(metadata_path),
                "--source-uri",
                "urn:test:paper",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out.strip().splitlines()[-1]
    item_id, relpath, _ = output.split("\t")
    sidecar_path = corpus_path / relpath
    sidecar = yaml.safe_load(
        sidecar_path.with_name(sidecar_path.name + ".biblicus.yml").read_text(encoding="utf-8")
    )
    shown_result = cli.main(["--corpus", str(corpus_path), "show", item_id])
    shown = json.loads(capsys.readouterr().out)

    assert shown_result == 0
    assert sidecar["title"] == "Curated Paper"
    assert sidecar["abstract"] == "A curated abstract."
    assert sidecar["biblicus"]["source"] == "urn:test:paper"
    assert shown["title"] == "Curated Paper"
    assert shown["tags"] == ["metadata-tag"]


def test_ingest_metadata_cli_date_flags_write_canonical_dates(tmp_path: Path, capsys):
    """
    CLI date flags write canonical nested dates and override metadata-file dates.
    """
    corpus_path = tmp_path / "corpus"
    source_path = tmp_path / "paper.pdf"
    metadata_path = tmp_path / "paper.metadata.yml"
    source_path.write_bytes(b"%PDF-1.4\n")
    metadata_path.write_text(
        yaml.safe_dump(
            {
                "title": "Dated Paper",
                "dates": {
                    "published_at": "2025-01-01",
                    "updated_at": "2025-01-02",
                },
                "date_provenance": {
                    "published_at": "source-metadata",
                    "updated_at": "source-metadata",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assert cli.main(["init", str(corpus_path)]) == 0
    assert (
        cli.main(
            [
                "--corpus",
                str(corpus_path),
                "ingest",
                str(source_path),
                "--metadata-file",
                str(metadata_path),
                "--source-uri",
                "urn:test:dated-paper",
                "--published-at",
                "2025-06-10",
                "--updated-at",
                "2025-06-11",
                "--retrieved-at",
                "2026-05-15T20:30:00Z",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out.strip().splitlines()[-1]
    _, relpath, _ = output.split("\t")
    sidecar_path = corpus_path / relpath
    sidecar = yaml.safe_load(
        sidecar_path.with_name(sidecar_path.name + ".biblicus.yml").read_text(encoding="utf-8")
    )

    assert sidecar["dates"] == {
        "published_at": "2025-06-10",
        "updated_at": "2025-06-11",
        "retrieved_at": "2026-05-15T20:30:00Z",
    }
    assert sidecar["date_provenance"] == {
        "published_at": "cli-argument",
        "updated_at": "cli-argument",
        "retrieved_at": "cli-argument",
    }
    assert "published" not in sidecar
    assert "updated" not in sidecar


def test_apply_ingest_date_overrides_rejects_legacy_top_level_dates():
    """
    Legacy top-level publication dates are rejected at the ingest boundary.
    """
    with pytest.raises(ValueError, match="dates.published_at"):
        cli._apply_ingest_date_overrides(
            metadata={"published": "2025-01-01"},
            published_at=None,
            updated_at=None,
            retrieved_at=None,
        )


def test_apply_ingest_date_overrides_rejects_invalid_date_format():
    """
    Publication date values must use a date or full timestamp format.
    """
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        cli._apply_ingest_date_overrides(
            metadata={},
            published_at="June 10, 2025",
            updated_at=None,
            retrieved_at=None,
        )
