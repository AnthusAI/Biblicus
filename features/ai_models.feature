Feature: AI client configuration models
  AI client configuration models parse providers and resolve credentials consistently.

  Scenario: LLM client resolve_api_key allows non-OpenAI providers
    When I attempt to resolve an LLM API key for provider "bedrock"
    Then the command succeeds

  Scenario: Embeddings client resolve_api_key allows non-OpenAI providers
    When I attempt to resolve an embeddings API key for provider "bedrock"
    Then the command succeeds

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

  Scenario: LLM client preserves provider-prefixed model identifiers
    When I resolve an LLM model identifier for provider "openai" and model "openai/gpt-4o-mini"
    Then the LLM model identifier equals "openai/gpt-4o-mini"

  Scenario: LLM client kwargs include extra params
    When I build LLM client kwargs with extra params
    Then the LLM kwargs include "openai_reasoning_effort" with value "high"

  Scenario: Embeddings client resolve_api_key returns explicit key
    When I resolve an embeddings API key with explicit key "api-123"
    Then the resolved API key equals "api-123"

  Scenario: Embeddings client kwargs include extra params
    When I build embeddings client kwargs with extra params
    Then the embeddings kwargs include "dimensions" with value "3"

  Scenario: Embeddings helper returns a single vector for convenience
    Given a fake OpenAI library is available that returns embedding vector "9.0,8.0" for input text "alpha"
    When I generate an embedding for text "alpha"
    Then the generated embedding equals "9.0,8.0"

  Scenario: Embeddings helper returns empty list for empty input
    When I generate embeddings for no texts
    Then the embeddings output includes 0 vectors

  Scenario: Embeddings client resolve_api_key reads the environment
    When I resolve an embeddings API key from environment "env-openai-key"
    Then the resolved API key equals "env-openai-key"

  Scenario: Completion fails fast when DSPy is missing
    Given the DSPy dependency is missing
    When I attempt to generate a completion with provider "openai"
    Then the command fails with exit code 2
    And standard error includes "biblicus[dspy]"

  Scenario: Embeddings fail fast when DSPy is missing
    Given the DSPy dependency is missing
    When I attempt to generate embeddings for texts "alpha"
    Then the command fails with exit code 2
    And standard error includes "biblicus[dspy]"

  Scenario: Embeddings fail fast when DSPy Embedder is unavailable
    Given the DSPy dependency is unavailable
    When I attempt to generate embeddings for texts "alpha"
    Then the command fails with exit code 2
    And standard error includes "biblicus[dspy]"
