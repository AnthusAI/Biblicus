@integration @dspy
Feature: Embeddings generation
  Embeddings are generated via provider-backed APIs and support batching and parallel requests.

  Scenario: OpenAI embeddings generate vectors for a batch and preserve order
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns embedding vector "1.0,2.0" for input text "alpha"
    And a fake OpenAI library is available that returns embedding vector "3.0,4.0" for input text "beta"
    When I generate embeddings for texts "alpha,beta"
    Then the embeddings output includes 2 vectors
    And the first embedding vector equals "1.0,2.0"
    And the second embedding vector equals "3.0,4.0"

  Scenario: Embeddings generator supports a single text convenience API
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns embedding vector "5.0,6.0" for input text "alpha"
    When I generate an embedding for text "alpha"
    Then the generated embedding equals "5.0,6.0"

  Scenario: Embeddings generator returns an empty list for empty input
    When I generate embeddings for no texts
    Then the embeddings output includes 0 vectors

  Scenario: Embeddings generator supports non-OpenAI providers
    Given a fake OpenAI library is available that returns embedding vector "1.0,2.0" for input text "alpha"
    When I attempt to generate embeddings with provider "bedrock"
    Then the command succeeds

  Scenario: Embeddings generator fails fast when DSPy dependency is unavailable
    Given the DSPy dependency is unavailable
    When I attempt to generate embeddings for texts "alpha"
    Then the command fails with exit code 2
    And standard error includes "biblicus[dspy]"

  Scenario: Embeddings generator fails fast when DSPy is missing entirely
    Given the DSPy dependency is missing
    When I attempt to generate embeddings for texts "alpha"
    Then the command fails with exit code 2
    And standard error includes "biblicus[dspy]"
