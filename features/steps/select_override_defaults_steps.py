from behave import then, when

from biblicus.extractors.select_override import SelectOverrideConfig
from biblicus.extractors.select_smart_override import SelectSmartOverrideConfig


@when("I build a SelectOverride config with defaults")
def step_build_select_override_default(context) -> None:
    context.override_config = SelectOverrideConfig()


@when("I build a SelectSmartOverride config with defaults")
def step_build_select_smart_override_default(context) -> None:
    context.override_config = SelectSmartOverrideConfig()


@then("the override media type patterns equal:")
def step_override_media_type_patterns_equal(context) -> None:
    patterns = context.override_config.media_type_patterns
    expected = [row["pattern"] for row in context.table]
    assert patterns == expected
