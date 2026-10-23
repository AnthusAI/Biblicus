"""
Closed vocabulary of entity kinds and relation types for the typed-entity extractor.

The vocabulary is per-publication data. Biblicus never hard-codes a kind or a relation type: every
kind and type in an extraction output is a key from this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import Field, model_validator

from .analysis.schema import AnalysisSchemaModel
from .retrieval import hash_text


def canonical_json(value: object) -> str:
    """
    Serialise a value to a canonical JSON string for hashing.

    :param value: JSON-compatible value.
    :type value: object
    :return: Compact JSON with sorted keys.
    :rtype: str
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


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
        return hash_text(canonical_json(self.model_dump(mode="json")))

    @property
    def entity_kind_keys(self) -> List[str]:
        """
        Entity kind keys in vocabulary order.

        :return: Entity kind keys.
        :rtype: list[str]
        """
        return [term.key for term in self.entity_kinds]


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


__all__ = [
    "Vocabulary",
    "VocabularyTerm",
    "canonical_json",
    "load_vocabulary",
]
