from __future__ import annotations

from pathlib import Path

from behave import given, then, when

from biblicus.user_config import load_user_config


def _write_user_config(path: Path, api_key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"openai:\n  api_key: {api_key}\n"
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


@then("no OpenAI API key is present in the loaded user configuration")
def step_no_openai_api_key_present(context) -> None:
    loaded = getattr(context, "loaded_user_config", None)
    assert loaded is not None
    assert loaded.openai is None
