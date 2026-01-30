from __future__ import annotations

import os
from pathlib import Path

from behave import given, then, when

from biblicus.user_config import load_user_config


def _write_user_config(path: Path, api_key: str, provider: str = "openai") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"{provider}:\n  api_key: {api_key}\n"
    path.write_text(text, encoding="utf-8")


@given('a local Biblicus user config exists with OpenAI API key "{api_key}"')
def step_local_user_config_exists(context, api_key: str) -> None:
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    path = Path(workdir) / ".biblicus" / "config.yml"
    _write_user_config(path, api_key)


@given('a home Biblicus user config exists with OpenAI API key "{api_key}"')
def step_home_user_config_exists(context, api_key: str) -> None:
    home = getattr(context, "workdir", None)
    assert home is not None
    path = Path(home) / "home" / ".biblicus" / "config.yml"
    _write_user_config(path, api_key)
    extra_env = getattr(context, "extra_env", None)
    if extra_env is None:
        extra_env = {}
        context.extra_env = extra_env
    extra_env["HOME"] = str(Path(home) / "home")


@when('I load user configuration from "{relative_path}"')
def step_load_user_config_from_path(context, relative_path: str) -> None:
    path = Path(context.workdir) / relative_path
    context.loaded_user_config = load_user_config(paths=[path])


@given('a local Biblicus user config exists with HuggingFace API key "{api_key}"')
def step_local_user_config_exists_huggingface(context, api_key: str) -> None:
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    path = Path(workdir) / ".biblicus" / "config.yml"
    _write_user_config(path, api_key, provider="huggingface")


@given('a home Biblicus user config exists with HuggingFace API key "{api_key}"')
def step_home_user_config_exists_huggingface(context, api_key: str) -> None:
    home = getattr(context, "workdir", None)
    assert home is not None
    path = Path(home) / "home" / ".biblicus" / "config.yml"
    _write_user_config(path, api_key, provider="huggingface")
    extra_env = getattr(context, "extra_env", None)
    if extra_env is None:
        extra_env = {}
        context.extra_env = extra_env
    extra_env["HOME"] = str(Path(home) / "home")


@then("no OpenAI API key is present in the loaded user configuration")
def step_no_openai_api_key_present(context) -> None:
    loaded = getattr(context, "loaded_user_config", None)
    assert loaded is not None
    assert loaded.openai is None


@then("no HuggingFace API key is present in the loaded user configuration")
def step_no_huggingface_api_key_present(context) -> None:
    loaded = getattr(context, "loaded_user_config", None)
    assert loaded is not None
    assert loaded.huggingface is None


@then('the loaded user configuration has HuggingFace API key "{api_key}"')
def step_huggingface_api_key_equals(context, api_key: str) -> None:
    loaded = getattr(context, "loaded_user_config", None)
    assert loaded is not None
    assert loaded.huggingface is not None
    assert loaded.huggingface.api_key == api_key


@given('a local Biblicus user config exists with Deepgram API key "{api_key}"')
def step_local_user_config_exists_deepgram(context, api_key: str) -> None:
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    path = Path(workdir) / ".biblicus" / "config.yml"
    _write_user_config(path, api_key, provider="deepgram")


@then('the loaded user configuration has Deepgram API key "{api_key}"')
def step_deepgram_api_key_equals(context, api_key: str) -> None:
    loaded = getattr(context, "loaded_user_config", None)
    assert loaded is not None
    assert loaded.deepgram is not None
    assert loaded.deepgram.api_key == api_key


@when("I call resolve_huggingface_api_key helper function")
def step_call_resolve_huggingface_api_key(context):
    from pathlib import Path

    from biblicus.user_config import resolve_huggingface_api_key

    # Temporarily override environment for test
    old_env_key = os.environ.get("HUGGINGFACE_API_KEY")
    old_env_home = os.environ.get("HOME")
    old_cwd = Path.cwd()
    extra_env = getattr(context, "extra_env", {})
    workdir = getattr(context, "workdir", None)

    # Set up environment
    if "HUGGINGFACE_API_KEY" in extra_env:
        os.environ["HUGGINGFACE_API_KEY"] = extra_env["HUGGINGFACE_API_KEY"]
    elif "HUGGINGFACE_API_KEY" in os.environ:
        del os.environ["HUGGINGFACE_API_KEY"]

    if "HOME" in extra_env:
        os.environ["HOME"] = extra_env["HOME"]

    # Change to workdir so load_user_config finds local config
    if workdir:
        os.chdir(workdir)

    try:
        context.resolved_api_key = resolve_huggingface_api_key()
    finally:
        # Restore environment
        os.chdir(old_cwd)

        if old_env_key is not None:
            os.environ["HUGGINGFACE_API_KEY"] = old_env_key
        elif "HUGGINGFACE_API_KEY" in os.environ:
            del os.environ["HUGGINGFACE_API_KEY"]

        if old_env_home is not None:
            os.environ["HOME"] = old_env_home
        elif "HOME" in os.environ:
            del os.environ["HOME"]


@when("I call resolve_deepgram_api_key helper function")
def step_call_resolve_deepgram_api_key(context):
    from pathlib import Path

    from biblicus.user_config import resolve_deepgram_api_key

    old_env_key = os.environ.get("DEEPGRAM_API_KEY")
    old_env_home = os.environ.get("HOME")
    old_cwd = Path.cwd()
    extra_env = getattr(context, "extra_env", {})
    workdir = getattr(context, "workdir", None)

    if "DEEPGRAM_API_KEY" in extra_env:
        os.environ["DEEPGRAM_API_KEY"] = extra_env["DEEPGRAM_API_KEY"]
    elif "DEEPGRAM_API_KEY" in os.environ:
        del os.environ["DEEPGRAM_API_KEY"]

    if "HOME" in extra_env:
        os.environ["HOME"] = extra_env["HOME"]

    if workdir:
        os.chdir(workdir)

    try:
        context.resolved_api_key = resolve_deepgram_api_key()
    finally:
        os.chdir(old_cwd)

        if old_env_key is not None:
            os.environ["DEEPGRAM_API_KEY"] = old_env_key
        elif "DEEPGRAM_API_KEY" in os.environ:
            del os.environ["DEEPGRAM_API_KEY"]

        if old_env_home is not None:
            os.environ["HOME"] = old_env_home
        elif "HOME" in os.environ:
            del os.environ["HOME"]
