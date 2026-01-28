Feature: Extractor guardrails
  Extractor prerequisites are validated explicitly.

  Scenario: Abstract extractor methods raise NotImplementedError
    When I call the abstract extractor methods
    Then the abstract extractor errors are raised

