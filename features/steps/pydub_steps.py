from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any, Dict

from behave import given, then


@dataclass
class _FakeAudioSegmentBehavior:
    frame_rate: int = 44100
    channels: int = 2


def _ensure_fake_audio_segment_behaviors(context) -> Dict[str, _FakeAudioSegmentBehavior]:
    behaviors = getattr(context, "fake_audio_segment_behaviors", None)
    if behaviors is None:
        behaviors = {}
        context.fake_audio_segment_behaviors = behaviors
    return behaviors


def _install_fake_pydub_module(context) -> None:
    already_installed = getattr(context, "_fake_pydub_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    if "pydub" in sys.modules:
        original_modules["pydub"] = sys.modules["pydub"]

    behaviors = _ensure_fake_audio_segment_behaviors(context)

    class AudioSegment:
        def __init__(self, source_format: str = "wav") -> None:
            self.source_format = source_format
            pydub_module.last_source_format = source_format  # type: ignore[attr-defined]
            self._frame_rate = 44100
            self._channels = 2

        @classmethod
        def from_file(cls, file_path: str, format: str) -> AudioSegment:
            pydub_module.last_load_path = file_path  # type: ignore[attr-defined]
            pydub_module.last_load_format = format  # type: ignore[attr-defined]
            segment = cls(source_format=format)

            # Apply behavior if set
            filename = file_path.rsplit("/", 1)[-1]
            behavior = behaviors.get(filename)
            if behavior:
                segment._frame_rate = behavior.frame_rate
                segment._channels = behavior.channels

            return segment

        def set_frame_rate(self, rate: int) -> AudioSegment:
            pydub_module.last_set_frame_rate = rate  # type: ignore[attr-defined]
            self._frame_rate = rate
            return self

        def set_channels(self, channels: int) -> AudioSegment:
            pydub_module.last_set_channels = channels  # type: ignore[attr-defined]
            self._channels = channels
            return self

        def export(self, path: str, format: str) -> None:
            pydub_module.last_export_path = path  # type: ignore[attr-defined]
            pydub_module.last_export_format = format  # type: ignore[attr-defined]

            # Write minimal audio data to the file
            with open(path, "wb") as f:
                if format == "wav":
                    # Minimal WAV header
                    f.write(b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data")
                elif format == "mp3":
                    f.write(b"ID3")
                elif format == "flac":
                    f.write(b"fLaC\x00\x00\x00\x22")
                elif format == "ogg":
                    f.write(b"OggS")
                else:
                    f.write(b"AUDIO")

    pydub_module = types.ModuleType("pydub")
    pydub_module.AudioSegment = AudioSegment
    pydub_module.last_load_path = None
    pydub_module.last_load_format = None
    pydub_module.last_export_path = None
    pydub_module.last_export_format = None
    pydub_module.last_set_frame_rate = None
    pydub_module.last_set_channels = None
    pydub_module.last_source_format = None

    sys.modules["pydub"] = pydub_module

    context._fake_pydub_installed = True
    context._fake_pydub_original_modules = original_modules


def _install_pydub_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_pydub_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    if "pydub" in sys.modules:
        original_modules["pydub"] = sys.modules["pydub"]

    pydub_module = types.ModuleType("pydub")
    sys.modules["pydub"] = pydub_module

    context._fake_pydub_unavailable_installed = True
    context._fake_pydub_unavailable_original_modules = original_modules


@given("a fake pydub library is available")
def step_fake_pydub_available(context) -> None:
    _install_fake_pydub_module(context)


@given("the pydub dependency is unavailable")
def step_pydub_dependency_unavailable(context) -> None:
    _install_pydub_unavailable_module(context)


@then('the audio conversion loaded format "{format}"')
def step_audio_conversion_loaded_format(context, format: str) -> None:
    _ = context
    pydub_module = sys.modules.get("pydub")
    assert pydub_module is not None
    actual = getattr(pydub_module, "last_load_format", None)
    assert actual == format


@then('the audio conversion exported format "{format}"')
def step_audio_conversion_exported_format(context, format: str) -> None:
    _ = context
    pydub_module = sys.modules.get("pydub")
    assert pydub_module is not None
    actual = getattr(pydub_module, "last_export_format", None)
    assert actual == format


@then('the audio conversion set frame rate to {rate:d}')
def step_audio_conversion_set_frame_rate(context, rate: int) -> None:
    _ = context
    pydub_module = sys.modules.get("pydub")
    assert pydub_module is not None
    actual = getattr(pydub_module, "last_set_frame_rate", None)
    assert actual == rate


@then('the audio conversion set channels to {channels:d}')
def step_audio_conversion_set_channels(context, channels: int) -> None:
    _ = context
    pydub_module = sys.modules.get("pydub")
    assert pydub_module is not None
    actual = getattr(pydub_module, "last_set_channels", None)
    assert actual == channels
