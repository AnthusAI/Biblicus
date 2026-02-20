from biblicus.evaluation.metrics.entity_metrics import normalize_entity_value


def test_normalize_entity_value_address():
    value = "123 Main St. Apt 4"
    normalized = normalize_entity_value(value, entity_type="address")
    assert "street" in normalized
    assert "apartment" in normalized
