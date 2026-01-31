@integration @openai
Feature: Text annotate integration
  Text annotate uses a language model to insert XML span tags with attributes.

  Scenario: Text annotate labels verbs with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text annotate to text "We run fast. They agree." with allowed attributes "label,phase,role" and prompt template:
      """
      Return all the verbs.
      """
    Then the text annotate has at least 1 spans
    And the text annotate uses only allowed attributes "label,phase,role"
    And the text annotate does not split words
