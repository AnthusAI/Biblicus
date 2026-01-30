from behave import given, when, then
import os


@when('I call resolve_api_key for OpenAI provider with no config override')
def step_call_resolve_api_key_openai(context):
    from biblicus.inference import resolve_api_key, ApiProvider
    from pathlib import Path

    # Temporarily override environment for test
    old_env_key = os.environ.get("OPENAI_API_KEY")
    old_env_home = os.environ.get("HOME")
    old_cwd = Path.cwd()
    extra_env = getattr(context, "extra_env", {})
    workdir = getattr(context, "workdir", None)

    # Set up environment
    if "OPENAI_API_KEY" in extra_env:
        os.environ["OPENAI_API_KEY"] = extra_env["OPENAI_API_KEY"]
    elif "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

    if "HOME" in extra_env:
        os.environ["HOME"] = extra_env["HOME"]

    # Change to workdir so load_user_config finds local config
    if workdir:
        os.chdir(workdir)

    try:
        context.resolved_api_key = resolve_api_key(ApiProvider.OPENAI, config_override=None)
    finally:
        # Restore environment
        os.chdir(old_cwd)

        if old_env_key is not None:
            os.environ["OPENAI_API_KEY"] = old_env_key
        elif "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        if old_env_home is not None:
            os.environ["HOME"] = old_env_home
        elif "HOME" in os.environ:
            del os.environ["HOME"]


@then('the resolved API key equals "{expected_key}"')
def step_check_resolved_api_key(context, expected_key):
    assert context.resolved_api_key == expected_key, f"Expected {expected_key}, got {context.resolved_api_key}"


@when('I call resolve_api_key for unknown provider with no config override')
def step_call_resolve_api_key_unknown(context):
    from biblicus.inference import resolve_api_key
    # Create a mock provider that's not in the enum
    class UnknownProvider:
        value = "unknown"
    context.resolved_api_key = resolve_api_key(UnknownProvider(), config_override=None)


@then('the resolved API key is None')
def step_check_resolved_api_key_is_none(context):
    assert context.resolved_api_key is None, f"Expected None, got {context.resolved_api_key}"
