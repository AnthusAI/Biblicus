from biblicus.evaluation.stt_benchmark import calculate_cer, calculate_wer


def test_calculate_wer_counts_operations():
    ref = "a b"
    hyp = "a c d"
    result = calculate_wer(ref, hyp)
    # expect one substitution (b->c) and one insertion (d)
    assert result["substitutions"] == 1
    assert result["insertions"] == 1
    assert result["deletions"] == 0
    assert result["wer"] > 0


def test_calculate_cer_handles_empty_reference():
    result = calculate_cer("", "abc")
    assert result["cer"] == 0.0
    assert result["reference_chars"] == 0
