"""
Topic granularity sweep workflow.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from pydantic import Field

from .analysis import get_analysis_backend
from .analysis.models import TopicModelingConfiguration, TopicModelingOutput
from .analysis.schema import AnalysisSchemaModel
from .constants import ANALYSIS_SCHEMA_VERSION
from .corpus import Corpus
from .models import ExtractionSnapshotReference
from .retrieval import hash_text
from .time import utc_now_iso

TOPIC_GRANULARITY_ANALYSIS_ID = "topic-granularity-sweep"


class TopicGranularityProfileResult(AnalysisSchemaModel):
    """
    Result for one granularity profile.

    :ivar profile: Profile identifier.
    :vartype profile: str
    :ivar topic_modeling_snapshot_id: Topic modeling snapshot produced by the profile.
    :vartype topic_modeling_snapshot_id: str
    :ivar topic_count: Non-outlier topic count.
    :vartype topic_count: int
    :ivar document_count: Documents modeled.
    :vartype document_count: int
    :ivar largest_topic_share: Largest topic document share.
    :vartype largest_topic_share: float
    :ivar in_target_range: Whether the topic count is inside the requested range.
    :vartype in_target_range: bool
    :ivar distance_to_target: Topic-count distance from the target range.
    :vartype distance_to_target: int
    """

    profile: str = Field(min_length=1)
    topic_modeling_snapshot_id: str = Field(min_length=1)
    topic_count: int = Field(ge=0)
    document_count: int = Field(ge=0)
    largest_topic_share: float = Field(ge=0)
    in_target_range: bool
    distance_to_target: int = Field(ge=0)


class TopicGranularityLabeledTopic(AnalysisSchemaModel):
    """
    Labeled topic summary from the selected profile rerun.

    :ivar topic_id: BERTopic topic identifier.
    :vartype topic_id: int
    :ivar label: Topic label.
    :vartype label: str
    :ivar document_count: Topic document count.
    :vartype document_count: int
    """

    topic_id: int
    label: str = Field(min_length=1)
    document_count: int = Field(ge=0)


class TopicGranularitySweepOutput(AnalysisSchemaModel):
    """
    Output for a topic granularity sweep.

    :ivar schema_version: Schema version.
    :vartype schema_version: int
    :ivar analysis_id: Analysis identifier.
    :vartype analysis_id: str
    :ivar snapshot_id: Sweep snapshot identifier.
    :vartype snapshot_id: str
    :ivar generated_at: Generation timestamp.
    :vartype generated_at: str
    :ivar inputs: Reproducibility inputs.
    :vartype inputs: dict[str, Any]
    :ivar target_topic_min: Minimum requested non-outlier topics.
    :vartype target_topic_min: int
    :ivar target_topic_max: Maximum requested non-outlier topics.
    :vartype target_topic_max: int
    :ivar selected_profile: Selected profile identifier.
    :vartype selected_profile: str
    :ivar selected_topic_modeling_snapshot_id: Unlabeled selected topic modeling snapshot.
    :vartype selected_topic_modeling_snapshot_id: str
    :ivar labeled_topic_modeling_snapshot_id: Labeled selected topic modeling snapshot.
    :vartype labeled_topic_modeling_snapshot_id: str
    :ivar profiles: Profile ranking results.
    :vartype profiles: list[TopicGranularityProfileResult]
    :ivar labeled_topics: Topic labels from the selected rerun.
    :vartype labeled_topics: list[TopicGranularityLabeledTopic]
    :ivar artifact_paths: Written artifact paths.
    :vartype artifact_paths: dict[str, str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    analysis_id: str = Field(default=TOPIC_GRANULARITY_ANALYSIS_ID)
    snapshot_id: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    target_topic_min: int = Field(ge=1)
    target_topic_max: int = Field(ge=1)
    selected_profile: str = Field(min_length=1)
    selected_topic_modeling_snapshot_id: str = Field(min_length=1)
    labeled_topic_modeling_snapshot_id: str = Field(min_length=1)
    profiles: List[TopicGranularityProfileResult] = Field(default_factory=list)
    labeled_topics: List[TopicGranularityLabeledTopic] = Field(default_factory=list)
    artifact_paths: Dict[str, str] = Field(default_factory=dict)


def run_topic_granularity_sweep(
    *,
    corpus: Corpus,
    configuration_name: str,
    configuration: Dict[str, object],
    extraction_snapshot: ExtractionSnapshotReference,
    target_topic_range: str,
) -> TopicGranularitySweepOutput:
    """
    Run coarse, balanced, and fine topic modeling profiles and label the winner.

    :param corpus: Corpus to analyze.
    :type corpus: biblicus.corpus.Corpus
    :param configuration_name: Human-readable base configuration name.
    :type configuration_name: str
    :param configuration: Topic modeling configuration mapping.
    :type configuration: dict[str, object]
    :param extraction_snapshot: Extraction snapshot reference.
    :type extraction_snapshot: biblicus.models.ExtractionSnapshotReference
    :param target_topic_range: Target topic range in ``min:max`` form.
    :type target_topic_range: str
    :return: Sweep output.
    :rtype: TopicGranularitySweepOutput
    """
    target_min, target_max = _parse_target_range(target_topic_range)
    base_config = TopicModelingConfiguration.model_validate(configuration)
    backend = get_analysis_backend("topic-modeling")
    profile_outputs: Dict[str, TopicModelingOutput] = {}
    profile_results: List[TopicGranularityProfileResult] = []

    for profile in _profile_names():
        profile_config = _profile_configuration(
            base_config=base_config,
            profile=profile,
            include_representation_model=False,
        )
        output = backend.run_analysis(
            corpus,
            configuration_name=f"{configuration_name}:{profile}:unlabeled",
            configuration=profile_config,
            extraction_snapshot=extraction_snapshot,
        )
        assert isinstance(output, TopicModelingOutput)
        profile_outputs[profile] = output
        profile_results.append(
            _profile_result(
                profile=profile,
                output=output,
                target_min=target_min,
                target_max=target_max,
            )
        )

    selected = _select_profile(profile_results)
    selected_output = profile_outputs[selected.profile]
    if base_config.bertopic_analysis.representation_model is not None:
        labeled_config = _profile_configuration(
            base_config=base_config,
            profile=selected.profile,
            include_representation_model=True,
        )
        labeled_output = backend.run_analysis(
            corpus,
            configuration_name=f"{configuration_name}:{selected.profile}:labeled",
            configuration=labeled_config,
            extraction_snapshot=extraction_snapshot,
        )
        assert isinstance(labeled_output, TopicModelingOutput)
    else:
        labeled_output = selected_output

    labeled_topics = [
        TopicGranularityLabeledTopic(
            topic_id=topic.topic_id,
            label=topic.label,
            document_count=topic.document_count,
        )
        for topic in labeled_output.report.topics
        if topic.topic_id != -1
    ]
    inputs = {
        "configuration_name": configuration_name,
        "extraction_snapshot": extraction_snapshot.as_string(),
        "target_topic_range": target_topic_range,
        "selected_profile": selected.profile,
        "profile_snapshot_ids": {
            result.profile: result.topic_modeling_snapshot_id for result in profile_results
        },
        "labeled_topic_modeling_snapshot_id": labeled_output.snapshot.snapshot_id,
    }
    snapshot_id = _sweep_snapshot_id(inputs=inputs, profiles=profile_results)
    output = TopicGranularitySweepOutput(
        snapshot_id=snapshot_id,
        generated_at=utc_now_iso(),
        inputs=inputs,
        target_topic_min=target_min,
        target_topic_max=target_max,
        selected_profile=selected.profile,
        selected_topic_modeling_snapshot_id=selected_output.snapshot.snapshot_id,
        labeled_topic_modeling_snapshot_id=labeled_output.snapshot.snapshot_id,
        profiles=profile_results,
        labeled_topics=labeled_topics,
        artifact_paths={},
    )
    artifact_paths = _write_sweep_artifacts(corpus=corpus, output=output)
    return output.model_copy(update={"artifact_paths": artifact_paths})


def topic_granularity_sweep_markdown(output: TopicGranularitySweepOutput) -> str:
    """
    Render sweep output as Markdown.

    :param output: Sweep output.
    :type output: TopicGranularitySweepOutput
    :return: Markdown report.
    :rtype: str
    """
    payload = output.model_dump(mode="json")
    lines = [
        "# Topic Granularity Sweep",
        "",
        f"- Snapshot: `{payload['snapshot_id']}`",
        f"- Target: {payload['target_topic_min']} to {payload['target_topic_max']} topics",
        f"- Selected profile: `{payload['selected_profile']}`",
        f"- Labeled topic modeling snapshot: `{payload['labeled_topic_modeling_snapshot_id']}`",
        "",
        "## Profiles",
        "",
        "| Profile | Topics | Largest Topic Share | In Target | Snapshot |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for profile in payload["profiles"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    profile["profile"],
                    str(profile["topic_count"]),
                    f"{float(profile['largest_topic_share']):.3f}",
                    "yes" if profile["in_target_range"] else "no",
                    f"`{profile['topic_modeling_snapshot_id']}`",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Labeled Topics",
            "",
            "| Topic ID | Label | Documents |",
            "| ---: | --- | ---: |",
        ]
    )
    for topic in payload["labeled_topics"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(topic["topic_id"]),
                    _markdown_cell(topic["label"]),
                    str(topic["document_count"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _parse_target_range(value: str) -> tuple[int, int]:
    if ":" not in value:
        raise ValueError("target_topic_range must use min:max form")
    raw_min, raw_max = value.split(":", 1)
    target_min = int(raw_min)
    target_max = int(raw_max)
    if target_min < 1 or target_max < target_min:
        raise ValueError("target_topic_range must have min >= 1 and max >= min")
    return target_min, target_max


def _profile_names() -> Sequence[str]:
    return ("coarse", "balanced", "fine")


def _profile_configuration(
    *,
    base_config: TopicModelingConfiguration,
    profile: str,
    include_representation_model: bool,
) -> Dict[str, object]:
    payload: Dict[str, object] = base_config.model_dump(mode="json")
    bertopic = payload.setdefault("bertopic_analysis", {})
    assert isinstance(bertopic, dict)
    parameters = bertopic.setdefault("parameters", {})
    assert isinstance(parameters, dict)
    hdbscan_model = bertopic.get("hdbscan_model")
    if not isinstance(hdbscan_model, dict):
        hdbscan_model = {"parameters": {}}
        bertopic["hdbscan_model"] = hdbscan_model
    hdbscan_parameters = hdbscan_model.setdefault("parameters", {})
    assert isinstance(hdbscan_parameters, dict)

    if profile == "coarse":
        parameters.update({"nr_topics": 10, "min_topic_size": 4})
        hdbscan_parameters.update(
            {
                "min_cluster_size": 4,
                "min_samples": 2,
                "cluster_selection_method": "eom",
                "prediction_data": True,
            }
        )
    elif profile == "balanced":
        parameters.update({"nr_topics": 15, "min_topic_size": 3})
        hdbscan_parameters.update(
            {
                "min_cluster_size": 3,
                "min_samples": 1,
                "cluster_selection_method": "eom",
                "prediction_data": True,
            }
        )
    elif profile == "fine":
        parameters.update({"nr_topics": None, "min_topic_size": 2})
        hdbscan_parameters.update(
            {
                "min_cluster_size": 2,
                "min_samples": 1,
                "cluster_selection_method": "leaf",
                "prediction_data": True,
            }
        )
    else:
        raise ValueError(f"Unknown granularity profile: {profile}")

    if not include_representation_model:
        bertopic["representation_model"] = None
    return payload


def _profile_result(
    *,
    profile: str,
    output: TopicModelingOutput,
    target_min: int,
    target_max: int,
) -> TopicGranularityProfileResult:
    non_outlier_topics = [topic for topic in output.report.topics if topic.topic_id != -1]
    topic_count = len(non_outlier_topics)
    document_count = output.report.bertopic_analysis.document_count
    largest_topic_count = max((topic.document_count for topic in output.report.topics), default=0)
    largest_topic_share = largest_topic_count / document_count if document_count else 0.0
    distance = 0
    if topic_count < target_min:
        distance = target_min - topic_count
    elif topic_count > target_max:
        distance = topic_count - target_max
    return TopicGranularityProfileResult(
        profile=profile,
        topic_modeling_snapshot_id=output.snapshot.snapshot_id,
        topic_count=topic_count,
        document_count=document_count,
        largest_topic_share=round(largest_topic_share, 6),
        in_target_range=target_min <= topic_count <= target_max,
        distance_to_target=distance,
    )


def _select_profile(
    profiles: Sequence[TopicGranularityProfileResult],
) -> TopicGranularityProfileResult:
    if not profiles:
        raise ValueError("Granularity sweep requires at least one profile")
    return sorted(
        profiles,
        key=lambda profile: (
            profile.distance_to_target,
            profile.largest_topic_share,
            -profile.topic_count,
            profile.profile,
        ),
    )[0]


def _sweep_snapshot_id(
    *, inputs: Dict[str, Any], profiles: Sequence[TopicGranularityProfileResult]
) -> str:
    payload = json.dumps(
        {
            "analysis_id": TOPIC_GRANULARITY_ANALYSIS_ID,
            "inputs": inputs,
            "profiles": [profile.model_dump(mode="json") for profile in profiles],
        },
        sort_keys=True,
    )
    return hash_text(payload)


def _write_sweep_artifacts(
    *, corpus: Corpus, output: TopicGranularitySweepOutput
) -> Dict[str, str]:
    run_dir = corpus.analysis_run_dir(
        analysis_id=TOPIC_GRANULARITY_ANALYSIS_ID,
        snapshot_id=output.snapshot_id,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "manifest": run_dir / "manifest.json",
        "output": run_dir / "output.json",
        "report": run_dir / "report.md",
    }
    artifact_paths = {key: str(path) for key, path in paths.items()}
    final_output = output.model_copy(update={"artifact_paths": artifact_paths})
    paths["manifest"].write_text(
        json.dumps(
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "analysis_id": TOPIC_GRANULARITY_ANALYSIS_ID,
                "snapshot_id": final_output.snapshot_id,
                "generated_at": final_output.generated_at,
                "inputs": final_output.inputs,
                "artifact_paths": artifact_paths,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["output"].write_text(final_output.model_dump_json(indent=2) + "\n", encoding="utf-8")
    paths["report"].write_text(
        topic_granularity_sweep_markdown(final_output) + "\n", encoding="utf-8"
    )
    latest_path = corpus.analysis_dir / TOPIC_GRANULARITY_ANALYSIS_ID / "latest.json"
    latest_path.write_text(
        json.dumps(
            {"snapshot_id": final_output.snapshot_id, "generated_at": final_output.generated_at},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact_paths


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
