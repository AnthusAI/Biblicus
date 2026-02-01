Feature: Markov analysis schema validation
  Markov analysis recipes are strict and raise explicit errors on invalid inputs.

  Scenario: Markov segmentation config requires llm configuration when method is llm
    When I attempt to validate a Markov recipe with segmentation method "llm" and no llm config
    Then a model validation error is raised
    And the validation error mentions "segmentation.llm is required"

  Scenario: Markov segmentation config requires span markup configuration when method is span markup
    When I attempt to validate a Markov recipe with segmentation method "span_markup" and no span markup config
    Then a model validation error is raised
    And the validation error mentions "segmentation.span_markup is required"

  Scenario: Markov span markup system prompt requires text placeholder
    When I attempt to validate a Markov recipe with span markup system prompt missing "{text}"
    Then a model validation error is raised
    And the validation error mentions "segmentation.span_markup.system_prompt"

  Scenario: Markov span markup prompt template must not include text placeholder
    When I attempt to validate a Markov recipe with span markup prompt template containing "{text}"
    Then a model validation error is raised
    And the validation error mentions "segmentation.span_markup.prompt_template"

  Scenario: Markov span markup requires label attribute when prepend label is enabled
    When I attempt to validate a Markov recipe with span markup prepend label enabled and no label attribute
    Then a model validation error is raised
    And the validation error mentions "segmentation.span_markup.label_attribute"

  Scenario: Markov span markup end label value requires verifier
    When I attempt to validate a Markov recipe with span markup end label value but no verifier
    Then a model validation error is raised
    And the validation error mentions "segmentation.span_markup.end_label_verifier"

  Scenario: Markov span markup end reject label value requires verifier
    When I attempt to validate a Markov recipe with span markup end reject label value but no verifier
    Then a model validation error is raised
    And the validation error mentions "segmentation.span_markup.end_label_verifier"

  Scenario: Markov span markup end label verifier system prompt requires text placeholder
    When I attempt to validate a Markov recipe with end label verifier system prompt missing "{text}"
    Then a model validation error is raised
    And the validation error mentions "end_label_verifier.system_prompt"

  Scenario: Markov span markup end label verifier prompt template must not include text placeholder
    When I attempt to validate a Markov recipe with end label verifier prompt template containing "{text}"
    Then a model validation error is raised
    And the validation error mentions "end_label_verifier.prompt_template"

  Scenario: Markov state naming requires client and prompts when enabled
    When I attempt to validate a Markov recipe with state naming enabled and missing requirements
    Then a model validation error is raised
    And the validation error mentions "report.state_naming.client"

  Scenario: Markov state naming requires system prompt when enabled
    When I attempt to validate a Markov recipe with state naming enabled and missing system prompt
    Then a model validation error is raised
    And the validation error mentions "report.state_naming.system_prompt"

  Scenario: Markov state naming requires prompt template when enabled
    When I attempt to validate a Markov recipe with state naming enabled and missing prompt template
    Then a model validation error is raised
    And the validation error mentions "report.state_naming.prompt_template"

  Scenario: Markov state naming accepts disabled config
    When I validate a Markov recipe with state naming disabled
    Then the Markov state naming is disabled

  Scenario: Markov state naming system prompt requires context pack placeholder
    When I attempt to validate a Markov recipe with state naming system prompt missing "{context_pack}"
    Then a model validation error is raised
    And the validation error mentions "state_naming.system_prompt"

  Scenario: Markov state naming prompt template must not include context pack placeholder
    When I attempt to validate a Markov recipe with state naming prompt template containing "{context_pack}"
    Then a model validation error is raised
    And the validation error mentions "state_naming.prompt_template"

  Scenario: Markov topic modeling requires a recipe when enabled
    When I attempt to validate a Markov recipe with topic modeling enabled and no recipe
    Then a model validation error is raised
    And the validation error mentions "topic_modeling.recipe is required"

  Scenario: Markov topic modeling requires single LLM extraction method
    When I attempt to validate a Markov recipe with topic modeling enabled and non-single LLM extraction
    Then a model validation error is raised
    And the validation error mentions "topic_modeling.recipe.llm_extraction.method must be 'single'"

  Scenario: Markov span markup accepts valid prompts
    When I validate a Markov recipe with span markup prompts
    Then the Markov segmentation method equals "span_markup"

  Scenario: Markov llm observations require client and prompt template when enabled
    When I attempt to validate a Markov recipe with llm observations enabled and missing requirements
    Then a model validation error is raised
    And the validation error mentions "llm_observations.client is required"

  Scenario: Markov llm observations require prompt template when enabled
    When I attempt to validate a Markov recipe with llm observations enabled and empty prompt template
    Then a model validation error is raised
    And the validation error mentions "llm_observations.prompt_template is required"

  Scenario: Markov embeddings validate text source
    When I attempt to validate a Markov recipe with embeddings enabled and invalid text source
    Then a model validation error is raised
    And the validation error mentions "embeddings.text_source"

  Scenario: Markov embeddings require client when enabled
    When I attempt to validate a Markov recipe with embeddings enabled and missing client
    Then a model validation error is raised
    And the validation error mentions "embeddings.client is required"

  Scenario: Markov observations validate text source
    When I attempt to validate a Markov recipe with observations text_source "unknown"
    Then a model validation error is raised
    And the validation error mentions "observations.text_source"

  Scenario: Markov recipe rejects unsupported schema versions
    When I attempt to validate a Markov recipe with schema version 2
    Then a model validation error is raised
    And the validation error mentions "Unsupported analysis schema version"

  Scenario: Markov segmentation config accepts enum method values
    When I validate a Markov recipe with enum segmentation method
    Then the Markov segmentation method equals "sentence"

  Scenario: Markov segmentation config rejects invalid method types
    When I attempt to validate a Markov recipe with invalid segmentation method type
    Then a model validation error is raised
    And the validation error mentions "segmentation.method must be"

  Scenario: Markov observations config accepts enum encoder values
    When I validate a Markov recipe with enum observations encoder
    Then the Markov observations encoder equals "tfidf"

  Scenario: Markov observations config rejects invalid encoder types
    When I attempt to validate a Markov recipe with invalid observations encoder type
    Then a model validation error is raised
    And the validation error mentions "observations.encoder must be"

  Scenario: Markov model config accepts enum family values
    When I validate a Markov recipe with enum model family
    Then the Markov model family equals "gaussian"

  Scenario: Markov model config rejects invalid family types
    When I attempt to validate a Markov recipe with invalid model family type
    Then a model validation error is raised
    And the validation error mentions "model.family must be"

  Scenario: Markov tfidf config rejects invalid ngram ranges
    When I attempt to validate a Markov recipe with tfidf ngram_range null
    Then a model validation error is raised
    And the validation error mentions "ngram_range"
    When I attempt to validate a Markov recipe with tfidf ngram_range [1]
    Then a model validation error is raised
    And the validation error mentions "tfidf.ngram_range must be"
    When I attempt to validate a Markov recipe with tfidf ngram_range [1, "a"]
    Then a model validation error is raised
    And the validation error mentions "tfidf.ngram_range must be"
    When I attempt to validate a Markov recipe with tfidf ngram_range [2, 1]
    Then a model validation error is raised
    And the validation error mentions "tfidf.ngram_range must be"
