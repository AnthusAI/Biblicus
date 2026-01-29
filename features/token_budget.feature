Feature: Token budget fitting
  A context pack may need to fit into a token budget for a specific model.
  Token counting depends on a tokenizer, so token fitting is an explicit stage.

  Scenario: Token fitting drops trailing blocks until the budget is met
    Given a retrieval result exists with evidence text:
      | text |
      | one two three |
      | four five six |
    When I build a context pack from that retrieval result joining with "\n\n"
    And I fit the context pack to a token budget of 3 tokens
    Then the context pack text equals:
      """
      one two three
      """

  Scenario: Token fitting keeps blocks when the budget allows
    Given a retrieval result exists with evidence text:
      | text |
      | one two three |
      | four |
    When I build a context pack from that retrieval result joining with "\n\n"
    And I fit the context pack to a token budget of 10 tokens
    Then the context pack text equals:
      """
      one two three

      four
      """

  Scenario: Token fitting can produce an empty context pack
    Given a retrieval result exists with evidence text:
      | text |
      | one two three |
    When I build a context pack from that retrieval result joining with "\n\n"
    And I fit the context pack to a token budget of 1 tokens
    Then the context pack text is empty
