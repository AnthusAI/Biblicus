from biblicus.evaluation.stt_benchmark import calculate_wer


def test_calculate_wer_tracks_deletions():
    # reference has an extra token that should be counted as a deletion
    reference = "hello world"
    hypothesis = "hello"
    result = calculate_wer(reference, hypothesis)
    assert result["deletions"] == 1
    assert result["wer"] > 0
