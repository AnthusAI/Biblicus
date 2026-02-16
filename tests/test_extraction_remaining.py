from pathlib import Path

from biblicus import extraction
from biblicus.models import CatalogItem


def test_load_stage_cache_hit_and_miss(tmp_path: Path):
    snapshot_dir = tmp_path
    item = CatalogItem(
        id="id1",
        relpath="r",
        sha256="x",
        bytes=1,
        media_type="text/plain",
        title=None,
        tags=[],
        metadata={},
        created_at="now",
        source_uri="file://"
    )
    stage_dir_name = extraction._pipeline_stage_dir_name(stage_index=1, extractor_id="s")
    text_path = snapshot_dir / "stages" / stage_dir_name / "text"
    text_path.mkdir(parents=True)
    (text_path / "id1.txt").write_text("hi", encoding="utf-8")
    meta_path = snapshot_dir / "stages" / stage_dir_name / "metadata"
    meta_path.mkdir(parents=True)
    (meta_path / "id1.json").write_text("{}", encoding="utf-8")

    def load(stage_index: int, extractor_id: str, target_item: CatalogItem):
        stage_dir = extraction._pipeline_stage_dir_name(stage_index=stage_index, extractor_id=extractor_id)
        text_relpath = Path("stages") / stage_dir / "text" / f"{target_item.id}.txt"
        text_file = snapshot_dir / text_relpath
        if not text_file.is_file():
            return None
        metadata_relpath = Path("stages") / stage_dir / "metadata" / f"{target_item.id}.json"
        meta_file = snapshot_dir / metadata_relpath
        metadata_value = {}
        if meta_file.is_file():
            metadata_value = extraction.json.loads(meta_file.read_text(encoding="utf-8"))
        return {
            "text_relpath": str(text_relpath),
            "metadata_relpath": str(metadata_relpath) if meta_file.is_file() else None,
            "text": text_file.read_text(encoding="utf-8"),
            "metadata": metadata_value,
        }

    assert load(1, "s", item) is not None
    assert load(1, "s", item.model_copy(update={"id": "missing"})) is None
