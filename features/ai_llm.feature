@integration @dspy
Feature: Provider-backed LLM utilities
  Biblicus provides a reusable completion interface with strict, user-facing errors.

  Scenario: Completion supports non-OpenAI providers
    Given a fake OpenAI library is available
    When I attempt to generate a completion with provider "bedrock"
    Then the command succeeds

  Scenario: Completion fails fast when DSPy dependency is unavailable
    Given the DSPy dependency is unavailable
    When I attempt to generate a completion with provider "openai"
    Then the command fails with exit code 2
    And standard error includes "biblicus[dspy]"

  Scenario: Completion fails fast when DSPy is missing entirely
    Given the DSPy dependency is missing
    When I attempt to generate a completion with provider "openai"
    Then the command fails with exit code 2
    And standard error includes "biblicus[dspy]"

  Scenario: Completion includes response format in the request
    Given a fake OpenAI library is available
    When I generate a completion with response format "json_object"
    Then the DSPy chat request used response format "json_object"
