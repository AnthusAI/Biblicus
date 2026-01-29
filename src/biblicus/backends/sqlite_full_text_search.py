"""
SQLite full-text search version five retrieval backend for Biblicus.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ..constants import CORPUS_DIR_NAME, RUNS_DIR_NAME
from ..corpus import Corpus
from ..frontmatter import parse_front_matter
from ..models import (
    Evidence,
    ExtractionRunReference,
    QueryBudget,
    RetrievalResult,
    RetrievalRun,
    parse_extraction_run_reference,
)
from ..retrieval import apply_budget, create_recipe_manifest, create_run_manifest, hash_text
from ..time import utc_now_iso


class SqliteFullTextSearchRecipeConfig(BaseModel):
    """
    Configuration for the SQLite full-text search backend.

    :ivar chunk_size: Maximum characters per chunk.
    :vartype chunk_size: int
    :ivar chunk_overlap: Overlap characters between chunks.
    :vartype chunk_overlap: int
    :ivar snippet_characters: Maximum characters to include in evidence snippets.
    :vartype snippet_characters: int
    :ivar extraction_run: Optional extraction run reference in the form extractor_id:run_id.
    :vartype extraction_run: str or None
    """

    model_config = ConfigDict(extra="forbid")

    chunk_size: int = Field(default=800, ge=1)
    chunk_overlap: int = Field(default=200, ge=0)
    snippet_characters: int = Field(default=400, ge=1)
    extraction_run: Optional[str] = None


class SqliteFullTextSearchBackend:
    """
    SQLite full-text search version five backend for practical local retrieval.

    :ivar backend_id: Backend identifier.
    :vartype backend_id: str
    """

    backend_id = "sqlite-full-text-search"

    def build_run(
        self, corpus: Corpus, *, recipe_name: str, config: Dict[str, object]
    ) -> RetrievalRun:
        """
        Build a full-text search version five index for the corpus.

        :param corpus: Corpus to build against.
        :type corpus: Corpus
        :param recipe_name: Human-readable recipe name.
        :type recipe_name: str
        :param config: Backend-specific configuration values.
        :type config: dict[str, object]
        :return: Run manifest describing the build.
        :rtype: RetrievalRun
        """
        recipe_config = SqliteFullTextSearchRecipeConfig.model_validate(config)
        catalog = corpus.load_catalog()
        recipe = create_recipe_manifest(
            backend_id=self.backend_id,
            name=recipe_name,
            config=recipe_config.model_dump(),
        )
        run = create_run_manifest(corpus, recipe=recipe, stats={}, artifact_paths=[])
        db_relpath = str(Path(CORPUS_DIR_NAME) / RUNS_DIR_NAME / f"{run.run_id}.sqlite")
        db_path = corpus.root / db_relpath
        corpus.runs_dir.mkdir(parents=True, exist_ok=True)
        extraction_reference = _resolve_extraction_reference(corpus, recipe_config)
        stats = _build_full_text_search_index(
            db_path=db_path,
            corpus=corpus,
            items=catalog.items.values(),
            recipe_config=recipe_config,
            extraction_reference=extraction_reference,
        )
        run = run.model_copy(update={"artifact_paths": [db_relpath], "stats": stats})
        corpus.write_run(run)
        return run

    def query(
        self,
        corpus: Corpus,
        *,
        run: RetrievalRun,
        query_text: str,
        budget: QueryBudget,
    ) -> RetrievalResult:
        """
        Query the SQLite full-text search index for evidence.

        :param corpus: Corpus associated with the run.
        :type corpus: Corpus
        :param run: Run manifest to use for querying.
        :type run: RetrievalRun
        :param query_text: Query text to execute.
        :type query_text: str
        :param budget: Evidence selection budget.
        :type budget: QueryBudget
        :return: Retrieval results containing evidence.
        :rtype: RetrievalResult
        """
        recipe_config = SqliteFullTextSearchRecipeConfig.model_validate(run.recipe.config)
        db_path = _resolve_run_db_path(corpus, run)
        candidates = _query_full_text_search_index(
            db_path=db_path,
            query_text=query_text,
            limit=_candidate_limit(budget.max_total_items),
            snippet_characters=recipe_config.snippet_characters,
        )
        sorted_candidates = sorted(
            candidates,
            key=lambda evidence_item: (-evidence_item.score, evidence_item.item_id),
        )
        ranked = [
            evidence_item.model_copy(
                update={
                    "rank": index,
                    "recipe_id": run.recipe.recipe_id,
                    "run_id": run.run_id,
                }
            )
            for index, evidence_item in enumerate(sorted_candidates, start=1)
        ]
        evidence = apply_budget(ranked, budget)
        stats = {"candidates": len(sorted_candidates), "returned": len(evidence)}
        return RetrievalResult(
            query_text=query_text,
            budget=budget,
            run_id=run.run_id,
            recipe_id=run.recipe.recipe_id,
            backend_id=self.backend_id,
            generated_at=utc_now_iso(),
            evidence=evidence,
            stats=stats,
        )


def _candidate_limit(max_total_items: int) -> int:
    """
    Expand a candidate limit beyond the requested evidence count.

    :param max_total_items: Requested evidence count.
    :type max_total_items: int
    :return: Candidate limit for backend search.
    :rtype: int
    """
    return max_total_items * 5


def _resolve_run_db_path(corpus: Corpus, run: RetrievalRun) -> Path:
    """
    Resolve the SQLite index path for a retrieval run.

    :param corpus: Corpus containing run artifacts.
    :type corpus: Corpus
    :param run: Retrieval run manifest.
    :type run: RetrievalRun
    :return: Path to the SQLite index file.
    :rtype: Path
    :raises FileNotFoundError: If the run does not have artifact paths.
    """
    if not run.artifact_paths:
        raise FileNotFoundError("Run has no artifact paths to query")
    return corpus.root / run.artifact_paths[0]


def _ensure_full_text_search_version_five(conn: sqlite3.Connection) -> None:
    """
    Verify SQLite full-text search version five support in the current runtime.

    :param conn: SQLite connection to test.
    :type conn: sqlite3.Connection
    :return: None.
    :rtype: None
    :raises RuntimeError: If full-text search version five support is unavailable.
    """
    try:
        cursor = conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_full_text_search USING fts5(content)"
        )
        cursor.close()
        conn.execute("DROP TABLE IF EXISTS chunks_full_text_search")
    except sqlite3.OperationalError as operational_error:
        raise RuntimeError(
            "SQLite full-text search version five is required but not available in this Python build"
        ) from operational_error


def _create_full_text_search_schema(conn: sqlite3.Connection) -> None:
    """
    Create the full-text search schema in a fresh SQLite database.

    :param conn: SQLite connection for schema creation.
    :type conn: sqlite3.Connection
    :return: None.
    :rtype: None
    """
    conn.execute(
        """
        CREATE VIRTUAL TABLE chunks_full_text_search USING fts5(
            content,
            item_id UNINDEXED,
            source_uri UNINDEXED,
            media_type UNINDEXED,
            relpath UNINDEXED,
            title UNINDEXED,
            start_offset UNINDEXED,
            end_offset UNINDEXED
        )
        """
    )


def _build_full_text_search_index(
    *,
    db_path: Path,
    corpus: Corpus,
    items: Iterable[object],
    recipe_config: SqliteFullTextSearchRecipeConfig,
    extraction_reference: Optional[ExtractionRunReference],
) -> Dict[str, int]:
    """
    Build a full-text search index from corpus items.

    :param db_path: Destination SQLite database path.
    :type db_path: Path
    :param corpus: Corpus containing the items.
    :type corpus: Corpus
    :param items: Catalog items to index.
    :type items: Iterable[object]
    :param recipe_config: Chunking and snippet configuration.
    :type recipe_config: SqliteFullTextSearchRecipeConfig
    :return: Index statistics.
    :rtype: dict[str, int]
    """
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(str(db_path))
    try:
        _ensure_full_text_search_version_five(connection)
        _create_full_text_search_schema(connection)
        chunk_count = 0
        item_count = 0
        text_item_count = 0
        for catalog_item in items:
            item_count += 1
            media_type = getattr(catalog_item, "media_type", "")
            relpath = getattr(catalog_item, "relpath", "")
            item_text = _load_text_from_item(
                corpus,
                item_id=str(getattr(catalog_item, "id", "")),
                relpath=str(relpath),
                media_type=str(media_type),
                extraction_reference=extraction_reference,
            )
            if item_text is None:
                continue
            text_item_count += 1
            title = getattr(catalog_item, "title", None)
            for start_offset, end_offset, chunk in _iter_chunks(
                item_text,
                chunk_size=recipe_config.chunk_size,
                chunk_overlap=recipe_config.chunk_overlap,
            ):
                connection.execute(
                    """
                    INSERT INTO chunks_full_text_search (
                        content,
                        item_id,
                        source_uri,
                        media_type,
                        relpath,
                        title,
                        start_offset,
                        end_offset
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk,
                        str(getattr(catalog_item, "id")),
                        getattr(catalog_item, "source_uri", None),
                        str(media_type),
                        str(relpath),
                        str(title) if title is not None else None,
                        start_offset,
                        end_offset,
                    ),
                )
                chunk_count += 1
        connection.commit()
        return {
            "items": item_count,
            "text_items": text_item_count,
            "chunks": chunk_count,
            "bytes": db_path.stat().st_size if db_path.exists() else 0,
        }
    finally:
        connection.close()


def _load_text_from_item(
    corpus: Corpus,
    *,
    item_id: str,
    relpath: str,
    media_type: str,
    extraction_reference: Optional[ExtractionRunReference],
) -> Optional[str]:
    """
    Load text content from a catalog item.

    :param corpus: Corpus containing the content.
    :type corpus: Corpus
    :param item_id: Item identifier.
    :type item_id: str
    :param relpath: Relative path to the content.
    :type relpath: str
    :param media_type: Media type for the content.
    :type media_type: str
    :param extraction_reference: Optional extraction run reference.
    :type extraction_reference: ExtractionRunReference or None
    :return: Text payload or None if not text.
    :rtype: str or None
    """
    if extraction_reference:
        extracted_text = corpus.read_extracted_text(
            extractor_id=extraction_reference.extractor_id,
            run_id=extraction_reference.run_id,
            item_id=item_id,
        )
        if isinstance(extracted_text, str) and extracted_text.strip():
            return extracted_text

    content_path = corpus.root / relpath
    raw_bytes = content_path.read_bytes()
    if media_type == "text/markdown":
        markdown_text = raw_bytes.decode("utf-8")
        parsed_document = parse_front_matter(markdown_text)
        return parsed_document.body
    if media_type.startswith("text/"):
        return raw_bytes.decode("utf-8")
    return None


def _resolve_extraction_reference(
    corpus: Corpus,
    recipe_config: SqliteFullTextSearchRecipeConfig,
) -> Optional[ExtractionRunReference]:
    """
    Resolve an extraction run reference from a recipe config.

    :param corpus: Corpus associated with the recipe.
    :type corpus: Corpus
    :param recipe_config: Parsed backend recipe configuration.
    :type recipe_config: SqliteFullTextSearchRecipeConfig
    :return: Parsed extraction reference or None.
    :rtype: ExtractionRunReference or None
    :raises FileNotFoundError: If an extraction run is referenced but not present.
    """
    if not recipe_config.extraction_run:
        return None
    extraction_reference = parse_extraction_run_reference(recipe_config.extraction_run)
    run_dir = corpus.extraction_run_dir(
        extractor_id=extraction_reference.extractor_id,
        run_id=extraction_reference.run_id,
    )
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Missing extraction run: {extraction_reference.as_string()}")
    return extraction_reference


def _iter_chunks(
    text: str, *, chunk_size: int, chunk_overlap: int
) -> Iterable[Tuple[int, int, str]]:
    """
    Yield overlapping chunks of text for indexing.

    :param text: Text to chunk.
    :type text: str
    :param chunk_size: Maximum chunk size.
    :type chunk_size: int
    :param chunk_overlap: Overlap between chunks.
    :type chunk_overlap: int
    :return: Iterable of (start, end, chunk) tuples.
    :rtype: Iterable[tuple[int, int, str]]
    :raises ValueError: If the overlap is greater than or equal to the chunk size.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    start_offset = 0
    text_length = len(text)
    while start_offset < text_length:
        end_offset = min(text_length, start_offset + chunk_size)
        yield start_offset, end_offset, text[start_offset:end_offset]
        if end_offset == text_length:
            break
        start_offset = end_offset - chunk_overlap


def _query_full_text_search_index(
    db_path: Path,
    query_text: str,
    limit: int,
    snippet_characters: int,
) -> List[Evidence]:
    """
    Query the SQLite full-text search index for evidence candidates.

    :param db_path: SQLite database path.
    :type db_path: Path
    :param query_text: Query text to execute.
    :type query_text: str
    :param limit: Maximum number of candidates to return.
    :type limit: int
    :param snippet_characters: Snippet length budget.
    :type snippet_characters: int
    :return: Evidence candidates.
    :rtype: list[Evidence]
    """
    connection = sqlite3.connect(str(db_path))
    try:
        rows = connection.execute(
            """
            SELECT
                content,
                item_id,
                source_uri,
                media_type,
                start_offset,
                end_offset,
                bm25(chunks_full_text_search) AS score
            FROM chunks_full_text_search
            WHERE chunks_full_text_search MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (query_text, limit),
        ).fetchall()
        evidence_items: List[Evidence] = []
        for (
            content,
            item_id,
            source_uri,
            media_type,
            start_offset,
            end_offset,
            score,
        ) in rows:
            snippet_text = content[:snippet_characters]
            evidence_items.append(
                Evidence(
                    item_id=str(item_id),
                    source_uri=str(source_uri) if source_uri is not None else None,
                    media_type=str(media_type),
                    score=float(-score),
                    rank=1,
                    text=snippet_text,
                    content_ref=None,
                    span_start=int(start_offset) if start_offset is not None else None,
                    span_end=int(end_offset) if end_offset is not None else None,
                    stage="full-text-search",
                    recipe_id="",
                    run_id="",
                    hash=hash_text(snippet_text),
                )
            )
        return evidence_items
    finally:
        connection.close()
