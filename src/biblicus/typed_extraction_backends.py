"""
Backends that propose typed entities and relations for the typed-entity extractor.

A backend receives an item text, the closed vocabulary and a score threshold, and returns candidate
mentions and relations as character offsets into that text. It never decides whether a mention
resolves to a registry entity; the extractor does that. Backends are replaceable: the extractor
depends only on :class:`TypedExtractionBackend`.

The default backend, :class:`Gliner2Backend`, wraps the GLiNER2 span model. Its heavy dependency is
an optional extra, installed with ``pip install "biblicus[typed-extraction]"``.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field

from .analysis.schema import AnalysisSchemaModel
from .typed_vocabulary import Vocabulary

GLINER2_BACKEND_ID = "gliner2"
GLINER2_MODEL = "fastino/gliner2-base-v1"
GLINER2_REVISION = "f9634218e53580c56edf0de97ca1a7d3f1c2354e"
REGISTRY_ONLY_BACKEND_ID = "registry-only"
WINDOW_MAXIMUM_CHARACTERS = 2000


class TypedExtractionDependencyError(ValueError):
    """
    A backend needs an optional dependency that is not installed.
    """


class BackendIdentity(AnalysisSchemaModel):
    """
    Identity of a backend, part of the cache key and of the output.

    :ivar id: Backend identifier.
    :vartype id: str
    :ivar model: Model name, or None for a backend without a model.
    :vartype model: str or None
    :ivar revision: Model revision, or None for a backend without a model.
    :vartype revision: str or None
    """

    id: str = Field(min_length=1)
    model: Optional[str] = None
    revision: Optional[str] = None


class BackendMention(AnalysisSchemaModel):
    """
    Candidate entity mention proposed by a backend.

    :ivar kind: Entity kind key from the vocabulary.
    :vartype kind: str
    :ivar start: Character offset of the first character in the item text.
    :vartype start: int
    :ivar end: Character offset after the last character in the item text.
    :vartype end: int
    :ivar score: Confidence between 0 and 1.
    :vartype score: float
    """

    kind: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    score: float = Field(ge=0, le=1)


class BackendRelation(AnalysisSchemaModel):
    """
    Candidate relation proposed by a backend, with both endpoints as offsets.

    :ivar type: Relation type key from the vocabulary.
    :vartype type: str
    :ivar subject_start: Start offset of the subject mention.
    :vartype subject_start: int
    :ivar subject_end: End offset of the subject mention.
    :vartype subject_end: int
    :ivar object_start: Start offset of the object mention.
    :vartype object_start: int
    :ivar object_end: End offset of the object mention.
    :vartype object_end: int
    :ivar score: Confidence between 0 and 1.
    :vartype score: float
    """

    type: str = Field(min_length=1)
    subject_start: int = Field(ge=0)
    subject_end: int = Field(ge=1)
    object_start: int = Field(ge=0)
    object_end: int = Field(ge=1)
    score: float = Field(ge=0, le=1)


class BackendExtraction(AnalysisSchemaModel):
    """
    Everything a backend proposes for one item text.

    :ivar mentions: Candidate entity mentions.
    :vartype mentions: list[BackendMention]
    :ivar relations: Candidate relations.
    :vartype relations: list[BackendRelation]
    """

    mentions: List[BackendMention] = Field(default_factory=list)
    relations: List[BackendRelation] = Field(default_factory=list)


class TypedExtractionBackend(ABC):
    """
    Interface of a typed extraction backend.

    :ivar identity: Backend, model and revision, used in the cache key and the output.
    :vartype identity: BackendIdentity
    :ivar cacheable: True when :meth:`extract` is expensive and its result should be cached.
    :vartype cacheable: bool
    """

    identity: BackendIdentity
    cacheable: bool = True

    @abstractmethod
    def extract(self, text: str, vocabulary: Vocabulary, threshold: float) -> BackendExtraction:
        """
        Propose entity mentions and relations for one item text.

        :param text: Item text.
        :type text: str
        :param vocabulary: Closed vocabulary; every returned kind and type must belong to it.
        :type vocabulary: biblicus.typed_vocabulary.Vocabulary
        :param threshold: Minimum confidence for a proposal.
        :type threshold: float
        :return: Proposed mentions and relations.
        :rtype: BackendExtraction
        """


class RegistryOnlyBackend(TypedExtractionBackend):
    """
    Backend that proposes nothing, so only registry matches appear in the output.
    """

    identity = BackendIdentity(id=REGISTRY_ONLY_BACKEND_ID)
    cacheable = False

    def extract(self, text: str, vocabulary: Vocabulary, threshold: float) -> BackendExtraction:
        """
        Return an empty proposal.

        :param text: Item text.
        :type text: str
        :param vocabulary: Closed vocabulary.
        :type vocabulary: biblicus.typed_vocabulary.Vocabulary
        :param threshold: Minimum confidence, unused.
        :type threshold: float
        :return: Empty extraction.
        :rtype: BackendExtraction
        """
        return BackendExtraction()


class Gliner2Backend(TypedExtractionBackend):
    """
    GLiNER2 span and relation model, run on paragraph-sized windows of the item text.

    The vocabulary label of each kind and relation type is the only instruction given to the model.
    Offsets are reported against the whole item text.
    """

    identity = BackendIdentity(
        id=GLINER2_BACKEND_ID, model=GLINER2_MODEL, revision=GLINER2_REVISION
    )

    def __init__(self, model: Optional[Any] = None) -> None:
        """
        Create the backend.

        The pinned checkpoint is loaded on first use, so a run served entirely from the cache never
        loads the model.

        :param model: A loaded GLiNER2 model, or None to load the pinned checkpoint on first use.
        :type model: Any or None
        """
        self._loaded_model = model

    @property
    def _model(self) -> Any:
        if self._loaded_model is None:
            self._loaded_model = _load_gliner2_model()
        return self._loaded_model

    def extract(self, text: str, vocabulary: Vocabulary, threshold: float) -> BackendExtraction:
        """
        Propose entity mentions and relations for one item text.

        :param text: Item text.
        :type text: str
        :param vocabulary: Closed vocabulary.
        :type vocabulary: biblicus.typed_vocabulary.Vocabulary
        :param threshold: Minimum confidence for a proposal.
        :type threshold: float
        :return: Proposed mentions and relations.
        :rtype: BackendExtraction
        :raises TypedExtractionDependencyError: If the ``typed-extraction`` extra is not installed.
        """
        kind_by_label = {term.label: term.key for term in vocabulary.entity_kinds}
        type_by_label = {term.label: term.key for term in vocabulary.relation_types}
        mentions: List[BackendMention] = []
        relations: List[BackendRelation] = []
        for window_start, window_end in paragraph_windows(
            text, maximum_characters=WINDOW_MAXIMUM_CHARACTERS
        ):
            window = text[window_start:window_end]
            mentions.extend(self._window_mentions(window, window_start, kind_by_label, threshold))
            if type_by_label:
                relations.extend(
                    self._window_relations(window, window_start, type_by_label, threshold)
                )
        return BackendExtraction(mentions=mentions, relations=relations)

    def _window_mentions(
        self, window: str, offset: int, kind_by_label: Dict[str, str], threshold: float
    ) -> List[BackendMention]:
        found = self._model.extract_entities(
            window,
            list(kind_by_label),
            threshold=threshold,
            include_spans=True,
            include_confidence=True,
        )["entities"]
        mentions = []
        for label, spans in found.items():
            for span in spans:
                start, end = _trim_span(window, span["start"], span["end"])
                if end > start:
                    mentions.append(
                        BackendMention(
                            kind=kind_by_label[label],
                            start=offset + start,
                            end=offset + end,
                            score=min(1.0, float(span["confidence"])),
                        )
                    )
        return mentions

    def _window_relations(
        self, window: str, offset: int, type_by_label: Dict[str, str], threshold: float
    ) -> List[BackendRelation]:
        found = self._model.extract_relations(
            window,
            list(type_by_label),
            threshold=threshold,
            include_spans=True,
            include_confidence=True,
        )["relation_extraction"]
        relations = []
        for label, pairs in found.items():
            for pair in pairs:
                subject = _trim_span(window, pair["head"]["start"], pair["head"]["end"])
                target = _trim_span(window, pair["tail"]["start"], pair["tail"]["end"])
                if subject[1] > subject[0] and target[1] > target[0]:
                    relations.append(
                        BackendRelation(
                            type=type_by_label[label],
                            subject_start=offset + subject[0],
                            subject_end=offset + subject[1],
                            object_start=offset + target[0],
                            object_end=offset + target[1],
                            score=min(
                                1.0,
                                float(min(pair["head"]["confidence"], pair["tail"]["confidence"])),
                            ),
                        )
                    )
        return relations


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


_TRIM_CHARACTERS = re.compile(r"[\s,.;:!?()\[\]{}\"']")


def _trim_span(window: str, start: int, end: int) -> Tuple[int, int]:
    while start < end and _TRIM_CHARACTERS.match(window[start]):
        start += 1
    while end > start and _TRIM_CHARACTERS.match(window[end - 1]):
        end -= 1
    return start, end


def _load_gliner2_model() -> Any:
    try:
        from gliner2 import GLiNER2
    except ImportError as error:
        raise TypedExtractionDependencyError(
            "The gliner2 backend needs the optional typed-extraction extra. "
            'Install it with: pip install "biblicus[typed-extraction]"'
        ) from error
    return GLiNER2.from_pretrained(GLINER2_MODEL, revision=GLINER2_REVISION)


_BACKEND_FACTORIES = {
    GLINER2_BACKEND_ID: Gliner2Backend,
    REGISTRY_ONLY_BACKEND_ID: RegistryOnlyBackend,
}
BACKEND_IDS = tuple(_BACKEND_FACTORIES)


def create_backend(backend_id: str) -> TypedExtractionBackend:
    """
    Create a backend by identifier.

    :param backend_id: ``gliner2`` or ``registry-only``.
    :type backend_id: str
    :return: Ready backend. The ``gliner2`` model loads on first use.
    :rtype: TypedExtractionBackend
    :raises KeyError: If the identifier is not one of :data:`BACKEND_IDS`.
    """
    return _BACKEND_FACTORIES[backend_id]()


__all__ = [
    "BACKEND_IDS",
    "BackendExtraction",
    "BackendIdentity",
    "BackendMention",
    "BackendRelation",
    "Gliner2Backend",
    "RegistryOnlyBackend",
    "TypedExtractionBackend",
    "TypedExtractionDependencyError",
    "create_backend",
    "paragraph_windows",
]
