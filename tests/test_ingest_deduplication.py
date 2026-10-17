from io import BytesIO

import pytest

from biblicus.corpus import Corpus
from biblicus.errors import IngestCollisionError
from biblicus.ingest_identity import canonical_ingest_identity_keys


def test_canonical_ingest_identity_keys_normalize_arxiv_sources():
    """Canonical ingest identities collapse arXiv source aliases."""
    keys = canonical_ingest_identity_keys(
        source_uri="https://arxiv.org/pdf/2505.22954v3.pdf",
        metadata={
            "arxiv_id": "2505.22954v1",
            "discovery_sources": [{"url": "https://huggingface.co/papers/2505.22954"}],
        },
    )

    assert keys == ["arxiv:2505.22954"]


def test_canonical_ingest_identity_keys_normalize_arxiv_doi_and_doi_url():
    """Canonical ingest identities retain arXiv and DOI keys from arXiv DOI forms."""
    keys = canonical_ingest_identity_keys(
        source_uri="https://doi.org/10.48550/arXiv.2505.22954",
        metadata={"doi": "DOI:10.48550/arXiv.2505.22954"},
    )

    assert keys == ["arxiv:2505.22954", "doi:10.48550/arxiv.2505.22954"]


def test_canonical_ingest_identity_keys_infer_nature_doi():
    """Canonical ingest identities infer DOI keys from supported publisher URLs."""
    keys = canonical_ingest_identity_keys(
        source_uri="https://www.nature.com/articles/s41586-023-06792-0",
        metadata={},
    )

    assert keys == ["doi:10.1038/s41586-023-06792-0"]


def test_ingest_blocks_same_arxiv_paper_from_different_source_forms(tmp_path):
    """Ingest rejects the same arXiv paper from landing and PDF source forms."""
    corpus = Corpus.init(tmp_path, force=True)
    first = corpus.ingest_item(
        b"%PDF-first",
        filename="first.pdf",
        media_type="application/pdf",
        metadata={"arxiv_id": "2505.22954v3"},
        source_uri="https://arxiv.org/abs/2505.22954",
    )

    with pytest.raises(IngestCollisionError) as error:
        corpus.ingest_item(
            b"%PDF-second",
            filename="second.pdf",
            media_type="application/pdf",
            metadata={},
            source_uri="https://arxiv.org/pdf/2505.22954",
        )

    assert error.value.existing_item_id == first.item_id
    assert error.value.collision_key == "arxiv:2505.22954"


def test_ingest_blocks_same_doi_from_different_source_forms(tmp_path):
    """Ingest rejects DOI aliases even when source URIs differ."""
    corpus = Corpus.init(tmp_path, force=True)
    first = corpus.ingest_item(
        b"%PDF-first",
        filename="first.pdf",
        media_type="application/pdf",
        metadata={"doi": "10.1234/Example.Article"},
        source_uri="https://doi.org/10.1234/Example.Article",
    )

    with pytest.raises(IngestCollisionError) as error:
        corpus.ingest_item(
            b"%PDF-second",
            filename="second.pdf",
            media_type="application/pdf",
            metadata={"doi": "https://doi.org/10.1234/example.article"},
            source_uri="https://publisher.example/articles/example",
        )

    assert error.value.existing_item_id == first.item_id
    assert error.value.collision_key == "doi:10.1234/example.article"


def test_ingest_blocks_same_bytes_from_different_sources(tmp_path):
    """Ingest rejects identical payload bytes from unrelated source URIs."""
    corpus = Corpus.init(tmp_path, force=True)
    first = corpus.ingest_item(
        b"same bytes",
        filename="first.bin",
        media_type="application/octet-stream",
        source_uri="urn:one",
    )

    with pytest.raises(IngestCollisionError) as error:
        corpus.ingest_item(
            b"same bytes",
            filename="second.bin",
            media_type="application/octet-stream",
            source_uri="urn:two",
        )

    assert error.value.existing_item_id == first.item_id
    assert error.value.collision_key == f"sha256:{first.sha256}"


def test_stream_ingest_blocks_same_bytes_without_leaving_temp_file(tmp_path):
    """Stream ingest removes temporary payload files after checksum collisions."""
    corpus = Corpus.init(tmp_path, force=True)
    first = corpus.ingest_item(
        b"stream bytes",
        filename="first.bin",
        media_type="application/octet-stream",
        source_uri="urn:stream-one",
    )

    with pytest.raises(IngestCollisionError) as error:
        corpus.ingest_item_stream(
            BytesIO(b"stream bytes"),
            filename="second.bin",
            media_type="application/octet-stream",
            source_uri="urn:stream-two",
        )

    assert error.value.collision_key == f"sha256:{first.sha256}"
    assert not list(tmp_path.rglob("*.tmp"))


def test_distinct_arxiv_papers_from_same_platform_ingest_normally(tmp_path):
    """Distinct arXiv identities from the same platform ingest successfully."""
    corpus = Corpus.init(tmp_path, force=True)
    first = corpus.ingest_item(
        b"%PDF-first",
        filename="first.pdf",
        media_type="application/pdf",
        metadata={"arxiv_id": "2505.22954"},
        source_uri="https://arxiv.org/abs/2505.22954",
    )
    second = corpus.ingest_item(
        b"%PDF-second",
        filename="second.pdf",
        media_type="application/pdf",
        metadata={"arxiv_id": "2603.18000"},
        source_uri="https://arxiv.org/abs/2603.18000",
    )

    assert first.item_id != second.item_id
