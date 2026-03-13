import importlib.util
import json
import sys
from pathlib import Path


def _load_script_module(module_name: str, script_name: str):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_markov_run_report_renders_state_labels_and_artifacts(tmp_path):
    module = _load_script_module("test_markov_run_report_module", "markov_run_report.py")
    corpus_dir = tmp_path / "corpus"
    metadata_dir = corpus_dir / "metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "catalog.json").write_text(
        json.dumps(
            {
                "items": {
                    "item-1": {
                        "relpath": "imports/remote/demo/item-1.txt",
                        "tags": ["label:residio"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    run_dir = tmp_path / "markov-run"
    run_dir.mkdir()
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "snapshot_id": "markov-snapshot",
                "corpus_uri": f"file://{corpus_dir}",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "output.json").write_text(
        json.dumps(
            {
                "snapshot": {
                    "snapshot_id": "markov-snapshot",
                    "configuration": {
                        "config": {
                            "segmentation": {"method": "llm_agent_phase"},
                            "observations": {"categorical_source": "topic_label"},
                            "model": {"family": "categorical"},
                            "topic_modeling": {"enabled": True},
                            "report": {"state_naming": {"enabled": True}},
                        }
                    },
                },
                "report": {
                    "states": [
                        {"state_id": 0, "label": "START", "exemplars": ["START"]},
                        {
                            "state_id": 1,
                            "label": "Greeting and information gathering",
                            "exemplars": ["Thank you for calling. Can I have your name please?"],
                        },
                        {"state_id": 2, "label": "END", "exemplars": ["END"]},
                    ],
                    "transitions": [
                        {"from_state": 0, "to_state": 1, "weight": 0.85},
                        {"from_state": 1, "to_state": 2, "weight": 0.77},
                    ],
                    "decoded_paths": [
                        {"item_id": "item-1", "state_sequence": [0, 1, 2]},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "segments.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"item_id": "item-1", "segment_index": 1, "text": "START"}),
                json.dumps(
                    {
                        "item_id": "item-1",
                        "segment_index": 2,
                        "text": "Thank you for calling. Can I have your name please?",
                    }
                ),
                json.dumps({"item_id": "item-1", "segment_index": 3, "text": "END"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    for artifact_name in (
        "observations.jsonl",
        "topic_modeling.json",
        "topic_assignments.jsonl",
        "transitions.png",
    ):
        (run_dir / artifact_name).write_text("{}", encoding="utf-8")

    report_path = module.build_report(run_dir)
    rendered = report_path.read_text(encoding="utf-8")

    assert "Greeting and information gathering (State 1)" in rendered
    assert "START (State 0) -> Greeting and information gathering (State 1): 0.8500" in rendered
    assert "`topic_modeling.json`: present" in rendered
    assert (
        "- Observation pipeline: `llm_agent_phase` segmentation feeding Categorical HMM over `topic_label` observations with segment topic modeling enabled"
        in rendered
    )


def test_topic_modeling_run_report_orders_topics_and_reports_examples(tmp_path):
    module = _load_script_module(
        "test_topic_modeling_run_report_module", "topic_modeling_run_report.py"
    )
    run_dir = tmp_path / "topic-run"
    run_dir.mkdir()
    (run_dir / "output.json").write_text(
        json.dumps(
            {
                "snapshot": {
                    "snapshot_id": "topic-snapshot",
                    "corpus_uri": "file:///tmp/residio-corpus",
                },
                "report": {
                    "text_collection": {"source_items": 1001},
                    "bertopic_analysis": {"document_count": 1001, "topic_count": 3},
                    "topics": [
                        {
                            "topic_id": 2,
                            "label": "Thermostat registration issue",
                            "label_source": "llm",
                            "document_count": 42,
                            "keywords": [
                                {"keyword": "registration", "score": 0.8},
                                {"keyword": "thermostat", "score": 0.7},
                            ],
                            "document_examples": [
                                "customer needs help registering the thermostat in the app"
                            ],
                        },
                        {
                            "topic_id": -1,
                            "label": "Outliers",
                            "label_source": "bertopic",
                            "document_count": 7,
                            "keywords": [],
                            "document_examples": [],
                        },
                        {
                            "topic_id": 1,
                            "label": "Sensor configuration question",
                            "label_source": "llm",
                            "document_count": 13,
                            "keywords": [
                                {"keyword": "sensor", "score": 0.6},
                            ],
                            "document_examples": [
                                "customer wants to configure a new wireless sensor"
                            ],
                        },
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    report_path = module.build_report(run_dir)
    rendered = report_path.read_text(encoding="utf-8")

    assert "- Outlier documents: 7" in rendered
    assert rendered.index("### Thermostat registration issue (Topic 2)") < rendered.index(
        "### Sensor configuration question (Topic 1)"
    )
    assert "registration: 0.8000" in rendered
    assert "customer needs help registering the thermostat in the app" in rendered
