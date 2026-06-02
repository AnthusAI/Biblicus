"""Tests for GROBID JIT runtime auto-start."""

from __future__ import annotations

import pytest

from biblicus import grobid_runtime


def test_resolve_grobid_base_url_defaults_to_localhost(monkeypatch):
    monkeypatch.delenv("BIBLICUS_GROBID_URL", raising=False)
    monkeypatch.delenv("PAPYRUS_GROBID_URL", raising=False)
    assert grobid_runtime.resolve_grobid_base_url() == "http://127.0.0.1:8070"


def test_ensure_grobid_running_skips_docker_when_already_alive(monkeypatch):
    monkeypatch.setattr(grobid_runtime, "grobid_is_alive", lambda _url: True)
    started = {"called": False}
    monkeypatch.setattr(
        grobid_runtime,
        "_start_or_reuse_local_grobid_container",
        lambda **_kwargs: started.__setitem__("called", True),
    )
    grobid_runtime._ENSURED_URL = None
    url = grobid_runtime.ensure_grobid_running("http://127.0.0.1:8070")
    assert url == "http://127.0.0.1:8070"
    assert started["called"] is False


def test_ensure_grobid_running_starts_local_container_when_down(monkeypatch):
    alive = {"value": False}

    def _alive(_url: str) -> bool:
        return alive["value"]

    def _start(**_kwargs):
        alive["value"] = True

    monkeypatch.setattr(grobid_runtime, "grobid_is_alive", _alive)
    monkeypatch.setattr(grobid_runtime, "_start_or_reuse_local_grobid_container", _start)
    monkeypatch.setattr(grobid_runtime, "_await_grobid_ready", lambda _url: None)
    grobid_runtime._ENSURED_URL = None
    url = grobid_runtime.ensure_grobid_running("http://127.0.0.1:8070")
    assert url == "http://127.0.0.1:8070"
    assert alive["value"] is True


def test_ensure_grobid_running_rejects_remote_without_auto_start(monkeypatch):
    monkeypatch.setattr(grobid_runtime, "grobid_is_alive", lambda _url: False)
    grobid_runtime._ENSURED_URL = None
    with pytest.raises(RuntimeError, match="Auto-start is only supported for localhost"):
        grobid_runtime.ensure_grobid_running("http://grobid.internal:8070")
