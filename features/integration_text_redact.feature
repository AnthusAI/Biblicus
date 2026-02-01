@integration @openai
Feature: Text redact integration
  Text redact uses a language model to insert XML span tags for redaction.

  Scenario: Text redact marks email addresses with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text redact to text "Contact us at demo@example.com for help." with prompt template:
      """
      Return all email addresses.
      """
    Then the text redact has at least 1 spans
    And the text redact does not split words

  Scenario: Text redact uses the default system prompt with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text redact to text "Contact us at demo@example.com for help." with prompt template and default system prompt:
      """
      Return all email addresses.
      """
    Then the text redact has at least 1 spans
    And the text redact does not split words

  Scenario: Text redact uses redaction types with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text redact to text "Account 1234 should be removed." with redaction types "pii" and prompt template:
      """
      Return the account identifiers.
      """
    Then the text redact has at least 1 spans
    And the text redact has a span with attribute "redact" equals "pii"
    And the text redact does not split words
