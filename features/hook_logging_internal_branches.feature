Feature: Hook logging internals
  Hook logging should redact source URIs safely.

  Scenario: Redaction preserves non-URI strings
    When I redact the source uri "just-a-string"
    Then the redacted source uri equals "just-a-string"
