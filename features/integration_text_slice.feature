@integration @openai
Feature: Text slice integration
  Text slice uses a language model to insert XML slice markers without re-emitting the full text.

  Scenario: Text slice extracts sentences with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text slice to text "First one. Second one. Third one." with prompt template:
      """
      Return each sentence as a slice.
      """
    Then the text slice has at least 3 slices

  Scenario: Text slice uses the default system prompt with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text slice to text "First one. Second one. Third one." with prompt template and default system prompt:
      """
      Return each sentence as a slice.
      """
    Then the text slice has at least 3 slices

  Scenario: Text slice groups agent and customer statements with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text slice to text "Agent: Hello. Agent: I can help. Customer: I need support. Customer: Thanks." with prompt template:
      """
      Return things that the agent said grouped together, and things the customer said in separate groups.
      """
    Then the text slice has at least 2 slices
