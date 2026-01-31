Feature: AI client configuration models
  AI client configuration models parse providers and resolve credentials consistently.

  Scenario: LLM client resolve_api_key rejects unsupported providers
    When I attempt to resolve an LLM API key for provider "bedrock"
    Then the command fails with exit code 2
    And standard error includes "Unsupported provider"

  Scenario: Embeddings client resolve_api_key rejects unsupported providers
    When I attempt to resolve an embeddings API key for provider "bedrock"
    Then the command fails with exit code 2
    And standard error includes "Unsupported provider"

  Scenario: Embeddings client config rejects invalid provider type
    When I attempt to validate an embeddings client config with invalid provider type
    Then a model validation error is raised
    And the validation error mentions "embeddings provider must be a string or AiProvider"

  Scenario: OpenAI API key is required when not provided and not configured
    When I attempt to resolve an embeddings API key without an explicit api key
    Then the command fails with exit code 2
    And standard error includes "requires an OpenAI API key"

  Scenario: AI module exposes lazy exports and rejects unknown ones
    When I access the Biblicus ai module exports
    Then the ai module exposes "AiProvider"
    And the ai module exposes "generate_completion"
    And the ai module exposes "generate_embeddings"
    And the ai module rejects unknown export "missing_export"
