import types
import sys

import pytest

from biblicus.evaluation.metrics import entity_metrics
from biblicus.evaluation.stt_benchmark import calculate_cer
from biblicus.extractors import aws_transcribe_stt


def test_entity_metrics_no_ground_truth():
    metrics = entity_metrics.calculate_entity_metrics({}, {})
    assert metrics["overall"]["exact_accuracy"] == 0.0
    assert metrics["overall"]["total_entities"] == 0.0


def test_calculate_cer_empty_reference():
    cer = calculate_cer("", "abc")
    assert cer["reference_chars"] == 0
    assert cer["cer"] == 0.0

