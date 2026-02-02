from behave import then, when
from pydantic import ValidationError

from biblicus.context_engine.models import (
    AssistantMessageSpec,
    ContextBudgetSpec,
    ContextDeclaration,
    ContextPackBudgetSpec,
    SystemMessageSpec,
    UserMessageSpec,
)


@when("I validate a Context budget with no fields")
def step_validate_context_budget_missing(context) -> None:
    context.model_error = None
    try:
        ContextBudgetSpec()
    except ValidationError as exc:
        context.model_error = exc


@when("I validate a Context pack budget with no fields")
def step_validate_context_pack_budget_missing(context) -> None:
    context.model_error = None
    try:
        ContextPackBudgetSpec()
    except ValidationError as exc:
        context.model_error = exc


@when("I validate a system message with no content or template")
def step_validate_system_message_missing(context) -> None:
    context.model_error = None
    try:
        SystemMessageSpec(type="system")
    except ValidationError as exc:
        context.model_error = exc


@when("I validate a user message with no content or template")
def step_validate_user_message_missing(context) -> None:
    context.model_error = None
    try:
        UserMessageSpec(type="user")
    except ValidationError as exc:
        context.model_error = exc


@when("I validate an assistant message with no content or template")
def step_validate_assistant_message_missing(context) -> None:
    context.model_error = None
    try:
        AssistantMessageSpec(type="assistant")
    except ValidationError as exc:
        context.model_error = exc


@when("I validate an assistant message with content and template")
def step_validate_assistant_message_both(context) -> None:
    context.model_error = None
    try:
        AssistantMessageSpec(type="assistant", content="hi", template="{input.query}")
    except ValidationError as exc:
        context.model_error = exc


@when("I validate an assistant message with content")
def step_validate_assistant_message_content(context) -> None:
    context.model_error = None
    context.assistant_message = AssistantMessageSpec(type="assistant", content="Hello assistant")


@when('I validate a Context declaration with pack "{name}"')
def step_validate_context_pack_single(context, name: str) -> None:
    context.context_decl = ContextDeclaration(name="support", packs=name)


@when("I validate a Context declaration with pack list:")
def step_validate_context_pack_list(context) -> None:
    packs = [row["name"] for row in context.table]
    context.context_decl = ContextDeclaration(name="support", packs=packs)


@when("I validate a Context declaration with pack entries:")
def step_validate_context_pack_entries(context) -> None:
    packs = []
    for row in context.table:
        entry = {"name": row["name"]}
        if "weight" in row and row["weight"]:
            entry["weight"] = float(row["weight"])
        packs.append(entry)
    context.context_decl = ContextDeclaration(name="support", packs=packs)


@when("I validate a Context declaration with a pack payload map")
def step_validate_context_pack_payload_map(context) -> None:
    payload = {"name": "support", "packs": {"name": "support_pack"}}
    context.context_decl = ContextDeclaration._coerce_pack_entries(payload)


@when("I validate a Context declaration model instance")
def step_validate_context_decl_instance(context) -> None:
    instance = ContextDeclaration(name="support", packs="support_pack")
    context.context_decl = ContextDeclaration.model_validate(instance)


@when("I validate a Context declaration validator with a model instance")
def step_validate_context_decl_validator_instance(context) -> None:
    instance = ContextDeclaration(name="support", packs="support_pack")
    context.context_decl = ContextDeclaration._coerce_pack_entries(instance)


@then('the context model error should mention "{message}"')
def step_context_model_error_mentions(context, message: str) -> None:
    error = getattr(context, "model_error", None)
    assert error is not None
    assert message in str(error)


@then('the normalized context pack name equals "{expected}"')
def step_context_pack_name_equals(context, expected: str) -> None:
    packs = context.context_decl.packs or []
    assert len(packs) == 1
    assert packs[0].name == expected


@then('the assistant message content is "{expected}"')
def step_assistant_message_content(context, expected: str) -> None:
    assert context.assistant_message.content == expected


@then("the normalized context pack names include:")
def step_context_pack_names_include(context) -> None:
    packs = context.context_decl.packs or []
    names = {pack.name for pack in packs}
    for row in context.table:
        assert row["name"] in names


@then("the context pack payload remains a mapping")
def step_context_pack_payload_mapping(context) -> None:
    assert isinstance(context.context_decl, dict)
    assert isinstance(context.context_decl.get("packs"), dict)
