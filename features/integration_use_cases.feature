@integration @openai
Feature: Use cases integration
  Some use-case demos exercise real external services. They are intentionally tagged so
  local test runs remain deterministic.

  Scenario: Mark sensitive spans for redaction (real model, default system prompt)
    When I run the use case demo script "text_redact_demo.py"
    Then the demo marked up text contains "<span>"
    And the demo marked up text contains "</span>"

