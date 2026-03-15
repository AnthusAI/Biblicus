from biblicus.evaluation.metrics.entity_metrics import normalize_entity_value


def test_normalize_entity_value_address():
    value = "123 Main St. Apt 4"
    normalized = normalize_entity_value(value, entity_type="address")
    assert "street" in normalized
    assert "apartment" in normalized


def test_normalize_entity_value_total():
    normalized = normalize_entity_value("Total: $1,234.50", entity_type="total")
    assert normalized == "1234.50"
