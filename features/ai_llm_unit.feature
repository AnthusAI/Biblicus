Feature: Provider-backed LLM utilities (unit)
  Non-integration coverage for provider errors and missing dependencies.

  Scenario: Completion rejects unsupported providers
    When I attempt to generate a completion with provider "bedrock"
    Then the command fails with exit code 2
    And standard error includes "Unsupported provider"

  Scenario: Completion fails fast when OpenAI dependency is unavailable
    Given the OpenAI dependency is unavailable
    When I attempt to generate a completion with provider "openai"
    Then the command fails with exit code 2
    And standard error includes "biblicus[openai]"
