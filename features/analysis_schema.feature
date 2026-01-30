Feature: Analysis schema validation
  Analysis schemas are strict and raise explicit errors on invalid inputs.

  Scenario: Unknown analysis backend is rejected
    When I attempt to resolve analysis backend "unknown-backend"
    Then the analysis backend error mentions "Unknown analysis backend"

  Scenario: Analysis backend base class is not implemented
    When I invoke the analysis backend base class
    Then a not implemented error is raised

  Scenario: LLM client config accepts enum provider
    When I validate an LLM client config with enum provider
    Then the LLM client config provider equals "openai"

  Scenario: LLM client config rejects invalid provider type
    When I attempt to validate an LLM client config with invalid provider type
    Then a model validation error is raised
    And the validation error mentions "llm client provider must be a string or LlmProvider"

  Scenario: LLM extraction config accepts enum method
    When I validate an LLM extraction config with enum method
    Then the LLM extraction config method equals "single"

  Scenario: LLM extraction config rejects invalid method type
    When I attempt to validate an LLM extraction config with invalid method type
    Then a model validation error is raised
    And the validation error mentions "llm_extraction.method must be a string or TopicModelingLlmExtractionMethod"

  Scenario: LLM fine-tuning handles missing document references
    When I run LLM fine-tuning with missing document references
    Then the fine-tuning topics labeled equals 1

  Scenario: Itemized response parses JSON string
    When I parse an itemized response JSON string
    Then the itemized response contains 2 items
