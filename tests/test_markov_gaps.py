import json
from pathlib import Path

from biblicus.analysis import markov


def test_load_topic_modeling_report_invalid_returns_none(tmp_path: Path, capsys):
    run_dir = tmp_path
    # valid JSON but incompatible schema to trigger validation fallback
    (run_dir / "topic_modeling.json").write_text('{"bad": "data"}', encoding="utf-8")
    assert markov._load_topic_modeling_report(run_dir=run_dir) is None


def test_load_llm_observation_cache_handles_bad_entries(tmp_path: Path):
    path = tmp_path / "cache.json"
    payload = {
        "segments": ["bad", {"segment_index": "x"}, {"segment_index": 2, "value": "ok"}],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    cache = markov._load_llm_observation_cache(path)
    assert cache == {2: {"segment_index": 2, "value": "ok"}}


def test_load_llm_observation_cache_missing_file():
    assert markov._load_llm_observation_cache(Path("/nonexistent/noway")) == {}
