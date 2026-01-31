@integration @openai
Feature: Text extract integration
  Text extract uses a language model to insert XML span tags without re-emitting the full text.

  Scenario: Text extract inserts tags with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text extract to text "Hello there. Please wrap the whole text in one span." with prompt template:
      """
      Return the entire text.
      """
    Then the text extract has at least one span
    And the text extract does not split words

  Scenario: Text extract extracts paragraphs with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text extract to text "Para one. || Para two. || Para three." with prompt template:
      """
      Return each paragraph.
      """
    Then the text extract has at least 3 spans
    And the text extract does not split words

  Scenario: Text extract extracts first sentences per paragraph with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text extract to text "First one. Second one. || Alpha first. Alpha second." with prompt template:
      """
      Return the first sentence from each paragraph.
      """
    Then the text extract has at least 2 spans
    And the text extract does not split words

  Scenario: Text extract extracts money-related quotes with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text extract to text "She said \"PAYMENT_QUOTE_001: I will pay $20 today.\" Then she left." with prompt template:
      """
      Return the quoted payment statement exactly as written, including the quotation marks.
      """
    Then the text extract has a span containing "$"
    And the text extract does not split words

  Scenario: Text extract returns all verbs with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text extract to text "We run fast. They agree." with prompt template:
      """
      Return all the verbs.
      """
    Then the text extract has at least one span
    And the text extract has a span containing "run"
    And the text extract does not split words

  Scenario: Text extract groups agent and customer statements with a live model
    Given an OpenAI API key is configured for this scenario
    When I apply text extract to text "Agent: Hello. Agent: I can help. Customer: I need support. Customer: Thanks." with prompt template:
      """
      Return things that the agent said grouped together, and things the customer said in separate groups.
      """
    Then the text extract has at least 2 spans
    And the text extract has a span containing "Agent:"
    And the text extract has a span containing "Customer:"
    And the text extract does not split words
