
from biblicus.evaluation.metrics.entity_metrics import (
    calculate_entity_f1,
    calculate_entity_metrics,
    calculate_string_similarity,
    normalize_entity_value,
)


def test_normalize_entity_address_and_company_variants():
    normalized_address = normalize_entity_value("123 St. Apt 4", "address")
    # street and apartment are expanded
    assert "street" in normalized_address and "apartment" in normalized_address

    normalized_company = normalize_entity_value("Acme Corp.", "company")
    # common suffix is stripped
    assert normalized_company == "acme"


def test_string_similarity_handles_empty_vs_nonempty():
    assert calculate_string_similarity("", "") == 1.0
    assert calculate_string_similarity("", "nonempty") == 0.0
    # triggers branch that swaps when first string shorter
    assert calculate_string_similarity("a", "ab") < 1.0


def test_entity_metrics_counts_exact_and_fuzzy_matches():
    ground_truth = {"company": "Acme LLC", "address": "123 Road"}
    extracted = {"company": "Acme llc", "address": "123 rd"}
    metrics = calculate_entity_metrics(ground_truth, extracted)
    company = metrics["company"]
    address = metrics["address"]
    assert company["exact_match"] == 1.0
    assert address["fuzzy_match"] == 1.0
    assert metrics["overall"]["total_entities"] == 2.0


def test_entity_metrics_custom_types_and_missing_ground_truth():
    ground_truth = {"total": "$12.50"}
    extracted = {"total": "total: 12.50", "address": "no gt"}
    metrics = calculate_entity_metrics(ground_truth, extracted, entity_types=["total", "address"])
    # ensure numeric parsing path and has_extraction without ground truth counted
    assert metrics["total"]["exact_match"] == 1.0
    assert metrics["address"]["has_ground_truth"] == 0.0
    assert metrics["address"]["has_extraction"] == 1.0


def test_entity_f1_counts_fp_and_fn_for_partial_matches():
    ground_truth_entities = [{"total": "12.00", "company": "Acme"}]
    extracted_entities = [{"total": "10.00", "company": ""}]
    scores = calculate_entity_f1(ground_truth_entities, extracted_entities, entity_types=["total", "company"])
    # total differs -> counts as both fp and fn
    assert scores["total"]["precision"] == 0.0
    assert scores["total"]["recall"] == 0.0
    # company missing in extraction should be false negative
    assert scores["company"]["recall"] == 0.0
    assert scores["company"]["precision"] == 0.0


def test_entity_f1_flags_false_positive_when_extraction_only():
    ground_truth_entities = [{"address": ""}]
    extracted_entities = [{"address": "123 st."}]
    scores = calculate_entity_f1(ground_truth_entities, extracted_entities, entity_types=["address"])
    assert scores["address"]["precision"] == 0.0
