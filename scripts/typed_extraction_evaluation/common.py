"""
Shared helpers for the typed extractor evaluation: normalisation, vocabulary and data loading.
"""

import json
import re
from pathlib import Path
from typing import List

import yaml

LAB_DIRECTORY = Path(__file__).resolve().parents[2] / "datasets" / "typed_extraction_lab"


def normalise_name(text: str) -> str:
    """
    Normalise an entity name so case, spacing and punctuation variants compare equal.

    :param text: Raw mention or key text.
    :type text: str
    :return: Lower-cased text with runs of non-alphanumeric characters collapsed to one space.
    :rtype: str
    """
    return re.sub(r"[^0-9a-z]+", " ", text.lower()).strip()


def load_vocabulary(path: Path = LAB_DIRECTORY / "vocabulary.yml") -> dict:
    """
    Load the closed vocabulary file.

    :param path: Vocabulary file path.
    :type path: pathlib.Path
    :return: Mapping with keys ``entity_kinds`` and ``relation_types``.
    :rtype: dict
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        "entity_kinds": [item["key"] for item in data["entity_kinds"]],
        "relation_types": [item["key"] for item in data["relation_types"]],
        "entity_labels": {item["key"]: item["label"] for item in data["entity_kinds"]},
        "relation_labels": {item["key"]: item["label"] for item in data["relation_types"]},
    }


def load_jsonl(path: Path) -> List[dict]:
    """
    Read a JSON Lines file.

    :param path: File path.
    :type path: pathlib.Path
    :return: One dictionary per non-empty line.
    :rtype: list[dict]
    """
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
