@integration @openai
Feature: Text link integration
  Text link uses a language model to insert id/ref span tags.

  Scenario: Text link connects repeated mentions with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text link to text "Acme launched a product. Later, Acme reported results." with prompt template:
      """
      Return repeated mentions of the same company and link repeats to the first mention.
      """
    Then the text link has at least 2 spans
    And the text link has an id span
    And the text link has a ref span
    And the text link does not split words

  Scenario: Text link uses the default system prompt with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text link to text "Acme launched a product. Later, Acme reported results." with prompt template and default system prompt:
      """
      Return repeated mentions of the same company and link repeats to the first mention.
      """
    Then the text link has at least 2 spans
    And the text link has an id span
    And the text link has a ref span
    And the text link does not split words
