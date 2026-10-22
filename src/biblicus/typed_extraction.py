"""
Typed entity and typed relation extraction driven by a closed vocabulary.

A publication defines a closed vocabulary of entity kinds and relation types. This module extracts
entities of those kinds, and relations of those types, from the extracted text of corpus items. Each
entity and relation carries evidence: the item identifier and character offsets into the item text.

Extraction runs in two steps. A registry alias matcher resolves mentions of already accepted
entities by exact match after normalising case, spacing and punctuation. A pluggable backend then
proposes the remaining entities and the relations. A mention is resolved only when its whole
normalised text equals an alias; prefixes are never merged and nothing is merged fuzzily.

The result is deterministic. Backend output is cached by text hash, vocabulary hash, backend
identity, model revision and threshold, and the output document contains no timestamps.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Sequence, Tuple

import yaml
from pydantic import Field, model_validator

from .analysis.schema import AnalysisSchemaModel
from .corpus import Corpus
from .models import ExtractionSnapshotReference, parse_extraction_snapshot_reference
from .retrieval import hash_text
from .typed_extraction_backends import (
    BackendExtraction,
    BackendIdentity,
    BackendMention,
    BackendRelation,
    TypedExtractionBackend,
)

TYPED_ENTITIES_ANALYSIS_ID = "typed-entities"
TYPED_ENTITIES_SCHEMA_VERSION = 1
SCORE_DECIMALS = 4
RUN_IDENTIFIER_LENGTH = 16
ENDPOINT_MINIMUM_OVERLAP = 0.5
OUTPUT_FILE_NAME = "output.json"
METADATA_FILE_NAME = "metadata.json"
CACHE_DIRECTORY_NAME = "cache"

EntityState = Literal["resolved", "proposed"]

_NON_ALPHANUMERIC_RUN = re.compile(r"[\W_]+")
_TOKEN = re.compile(r"[^\W_]+")
_JOINER = r"(?:[^\w\n]|_)+"
_LEFT_BOUNDARY = r"(?<!\w)(?<!\w[-./'’])"
_RIGHT_BOUNDARY = r"(?!\w)(?![-./'’]\w)"


def normalise_alias(text: str) -> str:
    """
    Normalise a mention or alias for exact comparison.

    Unicode compatibility forms are folded, letters are lower-cased and every run of characters
    that is not a letter or digit becomes a single space. Two texts that differ only in case,
    spacing or punctuation therefore normalise to the same string.

    :param text: Mention or alias text.
    :type text: str
    :return: Normalised text, possibly empty.
    :rtype: str
    """
    folded = unicodedata.normalize("NFKC", text).casefold()
    return _NON_ALPHANUMERIC_RUN.sub(" ", folded).strip()


class VocabularyTerm(AnalysisSchemaModel):
    """
    One entity kind or relation type of a closed vocabulary.

    :ivar key: Stable key written to the output.
    :vartype key: str
    :ivar label: Short natural-language name given to the backend.
    :vartype label: str
    :ivar description: Optional longer description for human readers.
    :vartype description: str or None
    """

    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: Optional[str] = None


class Vocabulary(AnalysisSchemaModel):
    """
    Closed vocabulary of entity kinds and relation types for one publication.

    :ivar version: Vocabulary version chosen by the publication.
    :vartype version: int
    :ivar publication: Publication the vocabulary belongs to.
    :vartype publication: str
    :ivar entity_kinds: Allowed entity kinds.
    :vartype entity_kinds: list[VocabularyTerm]
    :ivar relation_types: Allowed relation types.
    :vartype relation_types: list[VocabularyTerm]
    """

    version: int = Field(ge=1)
    publication: str = Field(min_length=1)
    entity_kinds: List[VocabularyTerm] = Field(min_length=1)
    relation_types: List[VocabularyTerm] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_unique_terms(self) -> "Vocabulary":
        for group_name, terms in (
            ("entity kind", self.entity_kinds),
            ("relation type", self.relation_types),
        ):
            for field_name in ("key", "label"):
                values = [getattr(term, field_name) for term in terms]
                duplicates = sorted({value for value in values if values.count(value) > 1})
                if duplicates:
                    raise ValueError(f"Duplicate {group_name} {field_name}: {duplicates[0]}")
        return self

    @property
    def hash(self) -> str:
        """
        Hash of the whole vocabulary content.

        :return: Hexadecimal digest that changes when any term changes.
        :rtype: str
        """
        return hash_text(_canonical_json(self.model_dump(mode="json")))

    @property
    def entity_kind_keys(self) -> List[str]:
        """
        Entity kind keys in vocabulary order.

        :return: Entity kind keys.
        :rtype: list[str]
        """
        return [term.key for term in self.entity_kinds]


class RegistryEntry(AnalysisSchemaModel):
    """
    One accepted entity of the registry.

    :ivar key: Stable entity key.
    :vartype key: str
    :ivar kind: Entity kind from the vocabulary.
    :vartype kind: str
    :ivar aliases: Surface forms that resolve to this entity.
    :vartype aliases: list[str]
    """

    key: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    aliases: List[str] = Field(default_factory=list)


class VocabularyIdentity(AnalysisSchemaModel):
    """
    Identity of the vocabulary used for a run.

    :ivar publication: Publication name.
    :vartype publication: str
    :ivar version: Vocabulary version.
    :vartype version: int
    :ivar hash: Vocabulary content hash.
    :vartype hash: str
    """

    publication: str = Field(min_length=1)
    version: int = Field(ge=1)
    hash: str = Field(min_length=1)


class BackendDescription(AnalysisSchemaModel):
    """
    Backend, model and threshold of a run.

    :ivar id: Backend identifier.
    :vartype id: str
    :ivar model: Model name, or None for a backend without a model.
    :vartype model: str or None
    :ivar revision: Model revision, or None for a backend without a model.
    :vartype revision: str or None
    :ivar threshold: Score threshold applied to model output.
    :vartype threshold: float
    """

    id: str = Field(min_length=1)
    model: Optional[str] = None
    revision: Optional[str] = None
    threshold: float = Field(gt=0, le=1)


class EntitySpan(AnalysisSchemaModel):
    """
    Character offsets into the item text.

    :ivar start: Offset of the first character.
    :vartype start: int
    :ivar end: Offset after the last character.
    :vartype end: int
    """

    start: int = Field(ge=0)
    end: int = Field(ge=1)

    @model_validator(mode="after")
    def _validate_order(self) -> "EntitySpan":
        if self.end <= self.start:
            raise ValueError("span end must be greater than start")
        return self


class TypedEntity(AnalysisSchemaModel):
    """
    One entity mention with its evidence.

    :ivar id: Entity identifier, unique within the item.
    :vartype id: str
    :ivar kind: Entity kind from the vocabulary.
    :vartype kind: str
    :ivar text: Mention text as it appears in the item.
    :vartype text: str
    :ivar state: ``resolved`` when the mention matched a registry alias, otherwise ``proposed``.
    :vartype state: str
    :ivar entity_key: Registry entity key for a resolved mention, otherwise None.
    :vartype entity_key: str or None
    :ivar span: Character offsets into the item text.
    :vartype span: EntitySpan
    :ivar score: Confidence between 0 and 1; 1.0 for a registry match.
    :vartype score: float
    """

    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    text: str = Field(min_length=1)
    state: EntityState
    entity_key: Optional[str] = None
    span: EntitySpan
    score: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _validate_state(self) -> "TypedEntity":
        if (self.state == "resolved") != (self.entity_key is not None):
            raise ValueError("entity_key is set exactly when state is resolved")
        return self


class TypedRelation(AnalysisSchemaModel):
    """
    One typed relation between two entities of the same item.

    :ivar id: Relation identifier, unique within the item.
    :vartype id: str
    :ivar type: Relation type from the vocabulary.
    :vartype type: str
    :ivar subject: Identifier of the subject entity.
    :vartype subject: str
    :ivar object: Identifier of the object entity.
    :vartype object: str
    :ivar state: ``resolved`` only when both endpoints are resolved, otherwise ``proposed``.
    :vartype state: str
    :ivar span: Character offsets covering both endpoints.
    :vartype span: EntitySpan
    :ivar score: Confidence between 0 and 1.
    :vartype score: float
    """

    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    object: str = Field(min_length=1)
    state: EntityState
    span: EntitySpan
    score: float = Field(ge=0, le=1)


class TypedItemResult(AnalysisSchemaModel):
    """
    Entities and relations extracted from one item.

    :ivar item_id: Corpus item identifier.
    :vartype item_id: str
    :ivar entities: Entities ordered by position.
    :vartype entities: list[TypedEntity]
    :ivar relations: Relations ordered by position.
    :vartype relations: list[TypedRelation]
    """

    item_id: str = Field(min_length=1)
    entities: List[TypedEntity] = Field(default_factory=list)
    relations: List[TypedRelation] = Field(default_factory=list)


class TypedEntitiesSummary(AnalysisSchemaModel):
    """
    Counts over the whole run.

    :ivar items: Items processed.
    :vartype items: int
    :ivar entities: Entities emitted.
    :vartype entities: int
    :ivar resolved: Entities resolved to a registry entity.
    :vartype resolved: int
    :ivar proposed: Entities proposed as new.
    :vartype proposed: int
    :ivar relations: Relations emitted.
    :vartype relations: int
    """

    items: int = Field(ge=0)
    entities: int = Field(ge=0)
    resolved: int = Field(ge=0)
    proposed: int = Field(ge=0)
    relations: int = Field(ge=0)


class TypedEntitiesOutput(AnalysisSchemaModel):
    """
    Typed entities and relations for a set of corpus items.

    The document is written to ``analysis/typed-entities/<run_id>/output.json`` and, when requested,
    to a caller-chosen directory. It contains no timestamps: the same inputs always produce
    byte-identical output.

    :ivar schema_version: Schema version.
    :vartype schema_version: int
    :ivar vocabulary: Identity of the vocabulary used.
    :vartype vocabulary: VocabularyIdentity
    :ivar backend: Backend, model and threshold used.
    :vartype backend: BackendDescription
    :ivar summary: Counts over the run.
    :vartype summary: TypedEntitiesSummary
    :ivar items: Results per item, ordered by item identifier.
    :vartype items: list[TypedItemResult]
    """

    schema_version: int = Field(default=TYPED_ENTITIES_SCHEMA_VERSION, ge=1)
    vocabulary: VocabularyIdentity
    backend: BackendDescription
    summary: TypedEntitiesSummary
    items: List[TypedItemResult] = Field(default_factory=list)


class TypedEntitiesRunMetadata(AnalysisSchemaModel):
    """
    Facts about one execution that must not appear in the deterministic output.

    :ivar run_id: Run identifier, equal to the run folder name.
    :vartype run_id: str
    :ivar created_at: Time the run finished, in Coordinated Universal Time.
    :vartype created_at: str
    :ivar elapsed_seconds: Wall-clock seconds spent extracting, model load excluded.
    :vartype elapsed_seconds: float
    :ivar items: Items processed.
    :vartype items: int
    :ivar backend_calls: Items sent to the backend.
    :vartype backend_calls: int
    :ivar cache_hits: Items served from the backend cache.
    :vartype cache_hits: int
    :ivar output_path: Path of the corpus copy of the output.
    :vartype output_path: str
    :ivar out_path: Path of the caller-chosen copy, or None.
    :vartype out_path: str or None
    """

    run_id: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    elapsed_seconds: float = Field(ge=0)
    items: int = Field(ge=0)
    backend_calls: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    output_path: str = Field(min_length=1)
    out_path: Optional[str] = None


class _Resolution(AnalysisSchemaModel):
    kind: str
    key: str


class TypedEntityRegistry:
    """
    Accepted entities with aliases, and the matcher that finds them in text.

    Every alias is normalised with :func:`normalise_alias`. Two entities may not share a
    normalised alias. A match in text must cover whole words: a candidate that continues into a
    longer name, such as ``Gemma 3`` inside ``Gemma-3-4B-it``, is not a match.
    """

    def __init__(self, entries: Sequence[RegistryEntry], vocabulary: Vocabulary) -> None:
        """
        Build the matcher from registry entries.

        :param entries: Accepted entities.
        :type entries: Sequence[RegistryEntry]
        :param vocabulary: Vocabulary every entry kind must belong to.
        :type vocabulary: Vocabulary
        :raises ValueError: If a kind is outside the vocabulary, an alias is empty or an alias
            belongs to two entities.
        """
        self._entries = list(entries)
        self._aliases: Dict[str, _Resolution] = {}
        allowed_kinds = set(vocabulary.entity_kind_keys)
        for entry in self._entries:
            if entry.kind not in allowed_kinds:
                raise ValueError(
                    f"Registry entry {entry.key} has kind {entry.kind} outside the vocabulary"
                )
            for alias in entry.aliases:
                normalised = normalise_alias(alias)
                if not normalised:
                    raise ValueError(f"Registry entry {entry.key} has an empty alias: {alias!r}")
                existing = self._aliases.get(normalised)
                if existing is not None and existing.key != entry.key:
                    raise ValueError(
                        f"Alias {alias!r} belongs to both {existing.key} and {entry.key}"
                    )
                self._aliases[normalised] = _Resolution(kind=entry.kind, key=entry.key)
        self._pattern = _compile_alias_pattern(self._aliases)

    @property
    def hash(self) -> str:
        """
        Hash of the registry content, independent of entry order.

        :return: Hexadecimal digest.
        :rtype: str
        """
        canonical = sorted(
            (entry.key, entry.kind, sorted(entry.aliases)) for entry in self._entries
        )
        return hash_text(_canonical_json(canonical))

    def resolve(self, text: str, kind: str) -> Optional[str]:
        """
        Resolve a mention to an entity key by whole-text normalised match and kind.

        :param text: Mention text.
        :type text: str
        :param kind: Kind proposed for the mention.
        :type kind: str
        :return: Entity key, or None when no alias of that kind equals the mention.
        :rtype: str or None
        """
        resolution = self._aliases.get(normalise_alias(text))
        if resolution is not None and resolution.kind == kind:
            return resolution.key
        return None

    def find(self, text: str) -> List[Tuple[int, int, str, str]]:
        """
        Find every registry alias in a text.

        :param text: Item text.
        :type text: str
        :return: ``(start, end, kind, entity key)`` tuples, ordered by position, not overlapping.
        :rtype: list[tuple[int, int, str, str]]
        """
        if self._pattern is None:
            return []
        found = []
        for match in self._pattern.finditer(text):
            resolution = self._aliases[normalise_alias(match.group())]
            found.append((match.start(), match.end(), resolution.kind, resolution.key))
        return found


def load_vocabulary(path: Path) -> Vocabulary:
    """
    Load a vocabulary file written in YAML or JSON.

    :param path: Vocabulary file path.
    :type path: pathlib.Path
    :return: Validated vocabulary.
    :rtype: Vocabulary
    :raises FileNotFoundError: If the file does not exist.
    :raises ValueError: If the content is not a valid vocabulary.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Vocabulary file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Vocabulary file {path} is not valid YAML: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"Vocabulary file {path} must contain a mapping")
    try:
        return Vocabulary.model_validate(data)
    except ValueError as error:
        raise ValueError(f"Invalid vocabulary {path}: {error}") from error


def load_registry(path: Path, vocabulary: Vocabulary) -> TypedEntityRegistry:
    """
    Load a registry file: a JSON list of ``{key, kind, aliases}`` objects.

    :param path: Registry file path.
    :type path: pathlib.Path
    :param vocabulary: Vocabulary the registry kinds must belong to.
    :type vocabulary: Vocabulary
    :return: Registry matcher.
    :rtype: TypedEntityRegistry
    :raises FileNotFoundError: If the file does not exist.
    :raises ValueError: If the file is not a valid registry.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Registry file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Registry file {path} is not valid JSON: {error}") from error
    if not isinstance(data, list):
        raise ValueError(f"Registry file {path} must contain a JSON list")
    try:
        entries = [RegistryEntry.model_validate(entry) for entry in data]
    except ValueError as error:
        raise ValueError(f"Invalid registry {path}: {error}") from error
    return TypedEntityRegistry(entries, vocabulary)


def paragraph_windows(text: str, *, maximum_characters: int = 2000) -> List[Tuple[int, int]]:
    """
    Split a text into paragraph-sized windows.

    Windows are separated by blank lines. A paragraph longer than the limit is cut at the last
    whitespace before the limit, or at the limit when it has none.

    :param text: Item text.
    :type text: str
    :param maximum_characters: Largest window size in characters.
    :type maximum_characters: int
    :return: ``(start, end)`` offsets of non-empty windows, in order.
    :rtype: list[tuple[int, int]]
    """
    windows: List[Tuple[int, int]] = []
    cursor = 0
    for separator in list(re.finditer(r"\n[ \t]*\n", text)) + [None]:
        paragraph_end = separator.start() if separator else len(text)
        next_cursor = separator.end() if separator else len(text)
        start = cursor
        while start < paragraph_end:
            end = min(start + maximum_characters, paragraph_end)
            if end < paragraph_end:
                cut = max(text.rfind(" ", start, end), text.rfind("\n", start, end))
                end = cut if cut > start else end
            if text[start:end].strip():
                windows.append((start, end))
            start = end
        cursor = next_cursor
    return windows


def extract_typed_entities(
    *,
    corpus: Corpus,
    vocabulary: Vocabulary,
    registry: Optional[TypedEntityRegistry],
    backend: TypedExtractionBackend,
    threshold: float,
    item_ids: Sequence[str],
    extraction_snapshot: Optional[str],
    out_dir: Optional[Path],
) -> TypedEntitiesOutput:
    """
    Extract typed entities and relations from the extracted text of corpus items.

    The output is written to ``analysis/typed-entities/<run_id>/output.json`` in the corpus, with
    ``metadata.json`` beside it, and to ``out_dir/output.json`` when ``out_dir`` is given.

    :param corpus: Corpus holding the items and the extraction snapshot.
    :type corpus: biblicus.corpus.Corpus
    :param vocabulary: Closed vocabulary.
    :type vocabulary: Vocabulary
    :param registry: Accepted entities, or None to propose every mention.
    :type registry: TypedEntityRegistry or None
    :param backend: Backend proposing entities and relations.
    :type backend: biblicus.typed_extraction_backends.TypedExtractionBackend
    :param threshold: Score threshold passed to the backend.
    :type threshold: float
    :param item_ids: Items to process; empty for every item with extracted text.
    :type item_ids: Sequence[str]
    :param extraction_snapshot: Extraction snapshot as ``extractor_id:snapshot_id``, or None for
        the latest snapshot.
    :type extraction_snapshot: str or None
    :param out_dir: Extra directory that receives ``output.json``, or None.
    :type out_dir: pathlib.Path or None
    :return: Typed entities and relations.
    :rtype: TypedEntitiesOutput
    :raises ValueError: If the corpus has no extraction snapshot or a requested item has no
        extracted text.
    :raises FileNotFoundError: If the extraction snapshot does not exist.
    """
    texts = _load_item_texts(
        corpus=corpus, extraction_snapshot=extraction_snapshot, item_ids=item_ids
    )
    identity = backend.identity
    description = BackendDescription(
        id=identity.id, model=identity.model, revision=identity.revision, threshold=threshold
    )
    run_id = _run_identifier(
        vocabulary=vocabulary,
        registry=registry,
        description=description,
        texts=texts,
    )
    started = time.perf_counter()
    counters = {"calls": 0, "hits": 0}
    items = [
        _extract_item(
            corpus=corpus,
            item_id=item_id,
            text=text,
            vocabulary=vocabulary,
            registry=registry,
            backend=backend,
            threshold=threshold,
            counters=counters,
        )
        for item_id, text in texts
    ]
    elapsed = time.perf_counter() - started
    output = TypedEntitiesOutput(
        vocabulary=VocabularyIdentity(
            publication=vocabulary.publication,
            version=vocabulary.version,
            hash=vocabulary.hash,
        ),
        backend=description,
        summary=_summarise(items),
        items=items,
    )
    _write_run(
        corpus=corpus,
        run_id=run_id,
        output=output,
        out_dir=out_dir,
        elapsed_seconds=elapsed,
        counters=counters,
    )
    return output


def typed_entities_json(output: TypedEntitiesOutput) -> str:
    """
    Render the output document exactly as it is written to disk.

    :param output: Typed entities output.
    :type output: TypedEntitiesOutput
    :return: Indented JSON with sorted keys and a trailing newline.
    :rtype: str
    """
    return json.dumps(output.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def typed_entities_run_dir(*, corpus: Corpus, run_id: str) -> Path:
    """
    Resolve the folder of a typed-entities run.

    :param corpus: Corpus containing the analysis artifacts.
    :type corpus: biblicus.corpus.Corpus
    :param run_id: Run identifier.
    :type run_id: str
    :return: Run folder.
    :rtype: pathlib.Path
    """
    return corpus.analysis_run_dir(analysis_id=TYPED_ENTITIES_ANALYSIS_ID, snapshot_id=run_id)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compile_alias_pattern(aliases: Dict[str, _Resolution]) -> Optional["re.Pattern[str]"]:
    if not aliases:
        return None
    ordered = sorted(aliases, key=lambda alias: (-len(alias.split()), -len(alias), alias))
    alternatives = [_JOINER.join(re.escape(token) for token in alias.split()) for alias in ordered]
    return re.compile(
        _LEFT_BOUNDARY + "(?:" + "|".join(alternatives) + ")" + _RIGHT_BOUNDARY,
        re.IGNORECASE,
    )


def _load_item_texts(
    *, corpus: Corpus, extraction_snapshot: Optional[str], item_ids: Sequence[str]
) -> List[Tuple[str, str]]:
    reference = _snapshot_reference(corpus, extraction_snapshot)
    manifest = corpus.load_extraction_snapshot_manifest(
        extractor_id=reference.extractor_id, snapshot_id=reference.snapshot_id
    )
    available = {
        result.item_id: result.final_text_relpath
        for result in manifest.items
        if result.final_text_relpath
    }
    requested = sorted(set(item_ids))
    missing = [item_id for item_id in requested if item_id not in available]
    if missing:
        raise ValueError(
            f"Item {missing[0]} has no extracted text in snapshot "
            f"{reference.extractor_id}:{reference.snapshot_id}"
        )
    selected = requested or sorted(available)
    snapshot_dir = corpus.extraction_snapshot_dir(
        extractor_id=reference.extractor_id, snapshot_id=reference.snapshot_id
    )
    return [
        (item_id, (snapshot_dir / available[item_id]).read_text(encoding="utf-8"))
        for item_id in selected
    ]


def _snapshot_reference(
    corpus: Corpus, extraction_snapshot: Optional[str]
) -> ExtractionSnapshotReference:
    if extraction_snapshot is not None:
        return parse_extraction_snapshot_reference(extraction_snapshot)
    latest = corpus.latest_extraction_snapshot_reference()
    if latest is None:
        raise ValueError(
            "The corpus has no extraction snapshot. Run `biblicus extract build` first or pass "
            "--extraction-snapshot."
        )
    return latest


def _run_identifier(
    *,
    vocabulary: Vocabulary,
    registry: Optional[TypedEntityRegistry],
    description: BackendDescription,
    texts: Sequence[Tuple[str, str]],
) -> str:
    digest = hash_text(
        _canonical_json(
            {
                "vocabulary": vocabulary.hash,
                "registry": registry.hash if registry else None,
                "backend": description.model_dump(mode="json"),
                "items": [[item_id, hash_text(text)] for item_id, text in texts],
            }
        )
    )
    return digest[:RUN_IDENTIFIER_LENGTH]


def _cache_path(
    *,
    corpus: Corpus,
    text: str,
    vocabulary: Vocabulary,
    identity: BackendIdentity,
    threshold: float,
) -> Path:
    key = hash_text(
        _canonical_json(
            {
                "text": hash_text(text),
                "vocabulary": vocabulary.hash,
                "backend": identity.id,
                "model": identity.model,
                "revision": identity.revision,
                "threshold": threshold,
            }
        )
    )
    return corpus.analysis_dir / TYPED_ENTITIES_ANALYSIS_ID / CACHE_DIRECTORY_NAME / f"{key}.json"


def _backend_extraction(
    *,
    corpus: Corpus,
    text: str,
    vocabulary: Vocabulary,
    backend: TypedExtractionBackend,
    threshold: float,
    counters: Dict[str, int],
) -> BackendExtraction:
    path = _cache_path(
        corpus=corpus,
        text=text,
        vocabulary=vocabulary,
        identity=backend.identity,
        threshold=threshold,
    )
    if backend.cacheable and path.is_file():
        counters["hits"] += 1
        return BackendExtraction.model_validate_json(path.read_text(encoding="utf-8"))
    counters["calls"] += 1
    extraction = backend.extract(text, vocabulary, threshold)
    if backend.cacheable:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(extraction.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return extraction


def _extract_item(
    *,
    corpus: Corpus,
    item_id: str,
    text: str,
    vocabulary: Vocabulary,
    registry: Optional[TypedEntityRegistry],
    backend: TypedExtractionBackend,
    threshold: float,
    counters: Dict[str, int],
) -> TypedItemResult:
    extraction = _backend_extraction(
        corpus=corpus,
        text=text,
        vocabulary=vocabulary,
        backend=backend,
        threshold=threshold,
        counters=counters,
    )
    mentions = _merge_mentions(text=text, registry=registry, proposed=extraction.mentions)
    entities = [
        TypedEntity(
            id=f"e{index}",
            kind=kind,
            text=text[start:end],
            state="resolved" if key else "proposed",
            entity_key=key,
            span=EntitySpan(start=start, end=end),
            score=round(score, SCORE_DECIMALS),
        )
        for index, (start, end, kind, key, score) in enumerate(mentions, start=1)
    ]
    relations = _build_relations(entities=entities, proposed=extraction.relations)
    return TypedItemResult(item_id=item_id, entities=entities, relations=relations)


def _merge_mentions(
    *,
    text: str,
    registry: Optional[TypedEntityRegistry],
    proposed: Iterable[BackendMention],
) -> List[Tuple[int, int, str, Optional[str], float]]:
    merged: List[Tuple[int, int, str, Optional[str], float]] = []
    registry_spans: List[Tuple[int, int]] = []
    if registry is not None:
        for start, end, kind, key in registry.find(text):
            merged.append((start, end, kind, key, 1.0))
            registry_spans.append((start, end))
    best: Dict[Tuple[int, int], BackendMention] = {}
    for mention in proposed:
        if any(mention.start < end and start < mention.end for start, end in registry_spans):
            continue
        current = best.get((mention.start, mention.end))
        if current is None or mention.score > current.score:
            best[(mention.start, mention.end)] = mention
    for mention in best.values():
        key = (
            registry.resolve(text[mention.start : mention.end], mention.kind) if registry else None
        )
        merged.append((mention.start, mention.end, mention.kind, key, mention.score))
    merged.sort(key=lambda row: (row[0], row[1], row[2]))
    return merged


def _overlap(left: Tuple[int, int], right: Tuple[int, int]) -> float:
    intersection = max(0, min(left[1], right[1]) - max(left[0], right[0]))
    union = (left[1] - left[0]) + (right[1] - right[0]) - intersection
    return intersection / union


def _endpoint_entity(
    entities: Sequence[TypedEntity], start: int, end: int
) -> Optional[TypedEntity]:
    best: Optional[TypedEntity] = None
    best_overlap = ENDPOINT_MINIMUM_OVERLAP
    for entity in entities:
        overlap = _overlap((entity.span.start, entity.span.end), (start, end))
        if overlap >= best_overlap:
            best, best_overlap = entity, overlap
    return best


def _build_relations(
    *, entities: Sequence[TypedEntity], proposed: Iterable[BackendRelation]
) -> List[TypedRelation]:
    by_triple: Dict[Tuple[str, str, str], Tuple[TypedEntity, TypedEntity, float]] = {}
    for relation in proposed:
        subject = _endpoint_entity(entities, relation.subject_start, relation.subject_end)
        target = _endpoint_entity(entities, relation.object_start, relation.object_end)
        if subject is None or target is None or subject.id == target.id:
            continue
        triple = (relation.type, subject.id, target.id)
        current = by_triple.get(triple)
        if current is None or relation.score > current[2]:
            by_triple[triple] = (subject, target, relation.score)
    ordered = sorted(
        by_triple.items(),
        key=lambda row: (
            min(row[1][0].span.start, row[1][1].span.start),
            max(row[1][0].span.end, row[1][1].span.end),
            row[0],
        ),
    )
    return [
        TypedRelation(
            id=f"r{index}",
            type=relation_type,
            subject=subject.id,
            object=target.id,
            state="resolved" if subject.state == target.state == "resolved" else "proposed",
            span=EntitySpan(
                start=min(subject.span.start, target.span.start),
                end=max(subject.span.end, target.span.end),
            ),
            score=round(score, SCORE_DECIMALS),
        )
        for index, ((relation_type, _, _), (subject, target, score)) in enumerate(ordered, start=1)
    ]


def _summarise(items: Sequence[TypedItemResult]) -> TypedEntitiesSummary:
    entities = [entity for item in items for entity in item.entities]
    resolved = sum(1 for entity in entities if entity.state == "resolved")
    return TypedEntitiesSummary(
        items=len(items),
        entities=len(entities),
        resolved=resolved,
        proposed=len(entities) - resolved,
        relations=sum(len(item.relations) for item in items),
    )


def _write_run(
    *,
    corpus: Corpus,
    run_id: str,
    output: TypedEntitiesOutput,
    out_dir: Optional[Path],
    elapsed_seconds: float,
    counters: Dict[str, int],
) -> None:
    text = typed_entities_json(output)
    run_dir = typed_entities_run_dir(corpus=corpus, run_id=run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / OUTPUT_FILE_NAME
    output_path.write_text(text, encoding="utf-8")
    out_path: Optional[Path] = None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / OUTPUT_FILE_NAME
        out_path.write_text(text, encoding="utf-8")
    metadata = TypedEntitiesRunMetadata(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=round(elapsed_seconds, 3),
        items=len(output.items),
        backend_calls=counters["calls"],
        cache_hits=counters["hits"],
        output_path=str(output_path),
        out_path=str(out_path) if out_path else None,
    )
    (run_dir / METADATA_FILE_NAME).write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "BackendDescription",
    "EntitySpan",
    "RegistryEntry",
    "TypedEntitiesOutput",
    "TypedEntitiesRunMetadata",
    "TypedEntitiesSummary",
    "TypedEntity",
    "TypedEntityRegistry",
    "TypedItemResult",
    "TypedRelation",
    "Vocabulary",
    "VocabularyIdentity",
    "VocabularyTerm",
    "extract_typed_entities",
    "load_registry",
    "load_vocabulary",
    "normalise_alias",
    "paragraph_windows",
    "typed_entities_json",
    "typed_entities_run_dir",
]
