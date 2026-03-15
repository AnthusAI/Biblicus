import os
from pathlib import Path

import importlib

from biblicus._vendor.dotyaml import interpolation, loader, transformer
from biblicus import __main__ as biblicus_main


def test_interpolation_replaces_env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_VALUE", "replaced")
    data = {"key": "{{ TEST_VALUE }}", "nested": {"inner": "{{ TEST_VALUE|fallback }}"}}
    result = interpolation.interpolate_env_vars(data)
    assert result["key"] == "replaced"
    assert result["nested"]["inner"] == "replaced"


def test_loader_load_yaml_view_merges_and_validates(tmp_path, monkeypatch):
    # disable dotenv for deterministic behavior
    monkeypatch.setattr(loader, "DOTENV_AVAILABLE", False)
    first = tmp_path / "a.yaml"
    second = tmp_path / "b.yaml"
    first.write_text("value: 1\nnested:\n  flag: true\n", encoding="utf-8")
    second.write_text("value: 2\nnested:\n  other: x\n", encoding="utf-8")
    composed = loader.load_yaml_view([first, second])
    assert composed["value"] == 2  # second overrides
    assert composed["nested"]["flag"] is True
    assert composed["nested"]["other"] == "x"

    config_loader = loader.ConfigLoader(prefix="APP", load_dotenv_first=False)
    # missing file returns empty mapping
    assert config_loader.load_from_yaml(tmp_path / "missing.yaml") == {}
    assert config_loader.load_from_env() == {}


def test_transformer_roundtrip_flatten_and_unflatten():
    original = {"section": {"flag": True, "count": 3}, "items": ["a", "b"]}
    flat = transformer.flatten_dict(original, prefix="APP")
    # ensure various value conversions are exercised
    assert flat["APP_SECTION_FLAG"] == "true"
    assert flat["APP_SECTION_COUNT"] == "3"
    assert flat["APP_ITEMS"] == "a,b"

    nested = transformer.unflatten_env_vars(flat, prefix="APP")
    # booleans and integers reconstructed
    assert nested["section"]["flag"] is True
    assert nested["section"]["count"] == 3
    assert nested["items"] == ["a", "b"]

    # convert_string_to_value additional branches
    assert transformer.convert_string_to_value("") is None
    assert transformer.convert_string_to_value("false") is False
    assert transformer.convert_string_to_value("1.5") == 1.5
    assert transformer.convert_string_to_value('{"a":1}') == {"a": 1}


def test_biblicus_main_import_does_not_execute_cli(monkeypatch):
    # Ensure importing the module is enough to cover it; __name__ != "__main__"
    module = importlib.reload(biblicus_main)
    assert hasattr(module, "main")
