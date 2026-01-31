@integration @openai
Feature: Provider-backed LLM utilities
  Biblicus provides a reusable completion interface with strict, user-facing errors.

  Scenario: Completion rejects unsupported providers
    When I attempt to generate a completion with provider "bedrock"
    Then the command fails with exit code 2
    And standard error includes "Unsupported provider"

  Scenario: Completion fails fast when OpenAI dependency is unavailable
    Given the OpenAI dependency is unavailable
    When I attempt to generate a completion with provider "openai"
    Then the command fails with exit code 2
    And standard error includes "biblicus[openai]"

  Scenario: Completion includes response format in the request
    Given a fake OpenAI library is available
    When I generate a completion with response format "json_object"
    Then the OpenAI chat request used response format "json_object"
