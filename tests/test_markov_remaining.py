import json

from biblicus.analysis import markov


def test_load_topic_modeling_report_recompute_on_invalid(tmp_path, capsys):
    report_path = tmp_path / "topic_modeling.json"
    # valid json but incompatible fields
    report_path.write_text(json.dumps({"bad": "data"}), encoding="utf-8")
    assert markov._load_topic_modeling_report(run_dir=tmp_path) is None
    assert "recomputing" in capsys.readouterr().err


def test_llm_observation_cache_bad_json_returns_empty(tmp_path):
    path = tmp_path / "obs.json"
    path.write_text("not json", encoding="utf-8")
    assert markov._load_llm_observation_cache(path) == {}
