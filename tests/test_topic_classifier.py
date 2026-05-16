from __future__ import annotations

import pytest
from pydantic import ValidationError

from biblicus.topic_classifier import (
    TopicClassifierSeedManifest,
    _validate_manifest_item_references,
)


def _valid_manifest_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "classifier_id": "classifier-lab-v1",
        "display_name": "Classifier Lab v1",
        "description": "Classifier manifest for tests.",
        "topics": [
            {
                "topic_uid": "agents",
                "display_name": "Agents",
                "description": "Agent systems.",
                "seed_item_ids": ["seed-a"],
                "holdout_item_ids": ["holdout-a"],
            },
            {
                "topic_uid": "speech",
                "display_name": "Speech",
                "description": "Speech recognition.",
                "seed_item_ids": ["seed-b"],
                "holdout_item_ids": [],
            },
        ],
        "unlabeled_policy": "use_minus_one",
    }


def test_topic_classifier_manifest_rejects_duplicate_topic_uid() -> None:
    """Reject duplicate stable topic identities."""
    payload = _valid_manifest_payload()
    payload["topics"][1]["topic_uid"] = "agents"

    with pytest.raises(ValidationError, match="Duplicate topic_uid"):
        TopicClassifierSeedManifest.model_validate(payload)


def test_topic_classifier_manifest_rejects_unknown_fields() -> None:
    """Reject manifest fields outside the strict schema."""
    payload = _valid_manifest_payload()
    payload["legacy_label_path"] = "folders"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TopicClassifierSeedManifest.model_validate(payload)


def test_topic_classifier_manifest_rejects_seed_reuse_across_topics() -> None:
    """Reject seed items reused across topic definitions."""
    payload = _valid_manifest_payload()
    payload["topics"][1]["seed_item_ids"] = ["seed-a"]

    with pytest.raises(ValidationError, match="Seed item seed-a is reused"):
        TopicClassifierSeedManifest.model_validate(payload)


def test_topic_classifier_manifest_rejects_holdout_listed_as_seed() -> None:
    """Reject item identifiers listed as both seed and holdout."""
    payload = _valid_manifest_payload()
    payload["topics"][1]["holdout_item_ids"] = ["seed-a"]

    with pytest.raises(ValidationError, match="Holdout item is also listed as a seed"):
        TopicClassifierSeedManifest.model_validate(payload)


def test_topic_classifier_manifest_rejects_missing_item_reference() -> None:
    """Reject seed manifests that point at unknown catalog items."""
    manifest = TopicClassifierSeedManifest.model_validate(_valid_manifest_payload())

    with pytest.raises(ValueError, match="references unknown item IDs"):
        _validate_manifest_item_references(manifest, ["seed-a", "seed-b"])
