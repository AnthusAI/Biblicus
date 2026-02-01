from __future__ import annotations

import json

from behave import then, when
from pydantic import ValidationError

from biblicus.analysis.models import (
    MarkovAnalysisModelFamily,
    MarkovAnalysisObservationsEncoder,
    MarkovAnalysisRecipeConfig,
    MarkovAnalysisSegmentationMethod,
)


@when('I attempt to validate a Markov recipe with segmentation method "{method}" and no llm config')
def step_attempt_validate_markov_recipe_missing_llm(context, method: str) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "segmentation": {"method": method},
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when(
    'I attempt to validate a Markov recipe with segmentation method "{method}" and no span markup config'
)
def step_attempt_validate_markov_recipe_missing_span_markup(context, method: str) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "segmentation": {"method": method},
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when(
    'I attempt to validate a Markov recipe with span markup system prompt missing "{token}"'
)
def step_attempt_validate_markov_recipe_span_markup_system_prompt_missing(
    context, token: str
) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return the segments.",
                        "system_prompt": f"Missing token {token.strip('{}')}",
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when(
    'I attempt to validate a Markov recipe with span markup prompt template containing "{token}"'
)
def step_attempt_validate_markov_recipe_span_markup_prompt_contains(
    context, token: str
) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": f"Return {token}.",
                        "system_prompt": "Current text:\n---\n{text}\n---\n",
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when(
    "I attempt to validate a Markov recipe with span markup prepend label enabled and no label attribute"
)
def step_attempt_validate_markov_recipe_span_markup_missing_label_attribute(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return the segments.",
                        "system_prompt": "Current text:\n---\n{text}\n---\n",
                        "prepend_label": True,
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with span markup end label value but no verifier")
def step_attempt_validate_markov_recipe_span_markup_end_label_missing_verifier(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return the segments.",
                        "system_prompt": "Current text:\n---\n{text}\n---\n",
                        "end_label_value": "End",
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with span markup end reject label value but no verifier")
def step_attempt_validate_markov_recipe_span_markup_end_reject_missing_verifier(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return the segments.",
                        "system_prompt": "Current text:\n---\n{text}\n---\n",
                        "end_reject_label_value": "Reject",
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when(
    'I attempt to validate a Markov recipe with end label verifier system prompt missing "{text_placeholder}"'
)
def step_attempt_validate_markov_recipe_end_verifier_system_prompt_missing(
    context, text_placeholder: str
) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return the segments.",
                        "system_prompt": "Current text:\n---\n{text}\n---\n",
                        "end_label_value": "End",
                        "end_label_verifier": {
                            "client": {
                                "provider": "openai",
                                "model": "gpt-4o-mini",
                                "api_key": "test-key",
                            },
                            "system_prompt": "Missing placeholder.",
                            "prompt_template": "Verify end label.",
                        },
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when(
    'I attempt to validate a Markov recipe with end label verifier prompt template containing "{text_placeholder}"'
)
def step_attempt_validate_markov_recipe_end_verifier_prompt_contains(
    context, text_placeholder: str
) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return the segments.",
                        "system_prompt": "Current text:\n---\n{text}\n---\n",
                        "end_label_value": "End",
                        "end_label_verifier": {
                            "client": {
                                "provider": "openai",
                                "model": "gpt-4o-mini",
                                "api_key": "test-key",
                            },
                            "system_prompt": "Verify end label:\n{text}",
                            "prompt_template": f"Verify {text_placeholder}",
                        },
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with state naming enabled and missing requirements")
def step_attempt_validate_markov_recipe_state_naming_missing(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "report": {"state_naming": {"enabled": True}},
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with state naming enabled and missing system prompt")
def step_attempt_validate_markov_recipe_state_naming_missing_system_prompt(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "report": {
                    "state_naming": {
                        "enabled": True,
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Name the state.",
                    }
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with state naming enabled and missing prompt template")
def step_attempt_validate_markov_recipe_state_naming_missing_prompt_template(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "report": {
                    "state_naming": {
                        "enabled": True,
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "system_prompt": "Context:\n{context_pack}",
                    }
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I validate a Markov recipe with state naming disabled")
def step_validate_markov_recipe_state_naming_disabled(context) -> None:
    config = MarkovAnalysisRecipeConfig.model_validate(
        {
            "schema_version": 1,
            "report": {"state_naming": {"enabled": False}},
            "model": {"family": "gaussian", "n_states": 2},
            "observations": {"encoder": "tfidf"},
        }
    )
    context.last_markov_recipe = config


@then("the Markov state naming is disabled")
def step_markov_state_naming_is_disabled(context) -> None:
    config = getattr(context, "last_markov_recipe", None)
    assert config is not None
    state_naming = config.report.state_naming
    assert state_naming is not None
    assert state_naming.enabled is False

@when(
    'I attempt to validate a Markov recipe with state naming system prompt missing "{context_pack}"'
)
def step_attempt_validate_markov_recipe_state_naming_missing_context_pack(
    context, context_pack: str
) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "report": {
                    "state_naming": {
                        "enabled": True,
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "system_prompt": "Missing context pack placeholder.",
                        "prompt_template": "Name the state.",
                    }
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when(
    'I attempt to validate a Markov recipe with state naming prompt template containing "{context_pack}"'
)
def step_attempt_validate_markov_recipe_state_naming_prompt_contains_context_pack(
    context, context_pack: str
) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "report": {
                    "state_naming": {
                        "enabled": True,
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "system_prompt": f"Context: {context_pack}",
                        "prompt_template": f"Name {context_pack}",
                    }
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with topic modeling enabled and no recipe")
def step_attempt_validate_markov_recipe_topic_modeling_enabled_without_recipe(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "topic_modeling": {"enabled": True},
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with topic modeling enabled and non-single LLM extraction")
def step_attempt_validate_markov_recipe_topic_modeling_non_single_llm_extraction(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "topic_modeling": {
                    "enabled": True,
                    "recipe": {
                        "schema_version": 1,
                        "llm_extraction": {
                            "enabled": True,
                            "method": "itemize",
                            "client": {
                                "provider": "openai",
                                "model": "gpt-4o-mini",
                                "api_key": "test-key",
                            },
                            "prompt_template": "{text}",
                        },
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I validate a Markov recipe with span markup prompts")
def step_validate_markov_recipe_span_markup_prompts(context) -> None:
    recipe = MarkovAnalysisRecipeConfig.model_validate(
        {
            "schema_version": 1,
            "segmentation": {
                "method": "span_markup",
                "span_markup": {
                    "client": {
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "api_key": "test-key",
                    },
                    "prompt_template": "Return the segments.",
                    "system_prompt": "Current text:\n---\n{text}\n---\n",
                },
            },
            "model": {"family": "gaussian", "n_states": 2},
            "observations": {"encoder": "tfidf"},
        }
    )
    context.markov_recipe = recipe
    context.last_markov_recipe = recipe


@when(
    "I attempt to validate a Markov recipe with llm observations enabled and missing requirements"
)
def step_attempt_validate_markov_recipe_llm_observations_missing(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "llm_observations": {"enabled": True},
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when(
    "I attempt to validate a Markov recipe with llm observations enabled and empty prompt template"
)
def step_attempt_validate_markov_recipe_llm_observations_empty_prompt(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "llm_observations": {
                    "enabled": True,
                    "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test-key"},
                    "prompt_template": "",
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with embeddings enabled and invalid text source")
def step_attempt_validate_markov_recipe_embeddings_invalid_source(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "embeddings": {
                    "enabled": True,
                    "text_source": "unknown",
                    "client": {
                        "provider": "openai",
                        "model": "text-embedding-3-small",
                        "api_key": "test-key",
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with embeddings enabled and missing client")
def step_attempt_validate_markov_recipe_embeddings_missing_client(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "embeddings": {"enabled": True, "text_source": "segment_text"},
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when('I attempt to validate a Markov recipe with observations text_source "{source}"')
def step_attempt_validate_markov_recipe_observations_text_source(context, source: str) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "observations": {"encoder": "tfidf", "text_source": source},
                "model": {"family": "gaussian", "n_states": 2},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with schema version {schema_version:d}")
def step_attempt_validate_markov_recipe_schema_version(context, schema_version: int) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": schema_version,
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I validate a Markov recipe with enum segmentation method")
def step_validate_markov_recipe_enum_segmentation_method(context) -> None:
    recipe = MarkovAnalysisRecipeConfig.model_validate(
        {
            "schema_version": 1,
            "segmentation": {"method": MarkovAnalysisSegmentationMethod.SENTENCE},
            "model": {"family": "gaussian", "n_states": 2},
            "observations": {"encoder": "tfidf"},
        }
    )
    context.last_markov_recipe = recipe


@then('the Markov segmentation method equals "{expected}"')
def step_markov_segmentation_method_equals(context, expected: str) -> None:
    recipe = getattr(context, "last_markov_recipe", None)
    assert recipe is not None
    assert recipe.segmentation.method.value == expected


@when("I attempt to validate a Markov recipe with invalid segmentation method type")
def step_attempt_validate_markov_recipe_invalid_segmentation_method_type(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "segmentation": {"method": 123},
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I validate a Markov recipe with enum observations encoder")
def step_validate_markov_recipe_enum_observations_encoder(context) -> None:
    recipe = MarkovAnalysisRecipeConfig.model_validate(
        {
            "schema_version": 1,
            "observations": {"encoder": MarkovAnalysisObservationsEncoder.TFIDF},
            "model": {"family": "gaussian", "n_states": 2},
        }
    )
    context.last_markov_recipe = recipe


@then('the Markov observations encoder equals "{expected}"')
def step_markov_observations_encoder_equals(context, expected: str) -> None:
    recipe = getattr(context, "last_markov_recipe", None)
    assert recipe is not None
    assert recipe.observations.encoder.value == expected


@when("I attempt to validate a Markov recipe with invalid observations encoder type")
def step_attempt_validate_markov_recipe_invalid_observations_encoder_type(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "observations": {"encoder": 123},
                "model": {"family": "gaussian", "n_states": 2},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I validate a Markov recipe with enum model family")
def step_validate_markov_recipe_enum_model_family(context) -> None:
    recipe = MarkovAnalysisRecipeConfig.model_validate(
        {
            "schema_version": 1,
            "model": {"family": MarkovAnalysisModelFamily.GAUSSIAN, "n_states": 2},
            "observations": {"encoder": "tfidf"},
        }
    )
    context.last_markov_recipe = recipe


@then('the Markov model family equals "{expected}"')
def step_markov_model_family_equals(context, expected: str) -> None:
    recipe = getattr(context, "last_markov_recipe", None)
    assert recipe is not None
    assert recipe.model.family.value == expected


@when("I attempt to validate a Markov recipe with invalid model family type")
def step_attempt_validate_markov_recipe_invalid_model_family_type(context) -> None:
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "model": {"family": 123, "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a Markov recipe with tfidf ngram_range {raw_json}")
def step_attempt_validate_markov_recipe_tfidf_ngram_range(context, raw_json: str) -> None:
    value = json.loads(raw_json)
    try:
        MarkovAnalysisRecipeConfig.model_validate(
            {
                "schema_version": 1,
                "observations": {"encoder": "tfidf", "tfidf": {"ngram_range": value}},
                "model": {"family": "gaussian", "n_states": 2},
            }
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc
