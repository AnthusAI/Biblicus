from pydantic import BaseModel

from biblicus import extraction
from biblicus.corpus import Corpus
from biblicus.extractors.pipeline import PipelineExtractorConfig


def test_extraction_log_interval_and_heartbeat(monkeypatch, tmp_path, capsys):
    corpus = Corpus.init(tmp_path)
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(exist_ok=True, parents=True)
    raw_file = raw_dir / "file.txt"
    raw_file.write_text("hello", encoding="utf-8")
    corpus.ingest_source(raw_file)

    def fake_get_extractor(eid):
        if eid == "pipeline":
            class DummyPipelineExtractor:
                extractor_id = "pipeline"

                def validate_config(self, config):  # noqa: D401
                    return PipelineExtractorConfig.model_validate(config)

            return DummyPipelineExtractor()

        if eid == "dummy":
            class DummyStageConfig(BaseModel):
                class Config:
                    extra = "forbid"

            class DummyExtractor:
                extractor_id = "dummy"

                def validate_config(self, config):  # noqa: D401
                    return DummyStageConfig(**config)

                def extract_text(  # noqa: D401,ARG002
                    self, corpus, item, config, previous_extractions
                ):
                    return extraction.ExtractedText(text="", producer_extractor_id=eid)

            return DummyExtractor()

        raise KeyError(eid)

    monkeypatch.setattr(extraction, "get_extractor", fake_get_extractor)
    result = extraction.build_extraction_snapshot(
        corpus=corpus,
        extractor_id="pipeline",
        configuration_name="cfg",
        configuration={"stages": [{"extractor_id": "dummy", "configuration": {}}]},
        force=True,
        max_workers=1,
    )
    stderr_output = capsys.readouterr().err
    assert "processed 1/1" in stderr_output
    assert result.stats["total_items"] == 1
    assert result.stats["errored_items"] == 1
    assert result.stats["extracted_items"] == 0
