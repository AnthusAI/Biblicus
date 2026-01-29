Feature: Context pack building
  A context pack is the text that your application sends to a large language model.
  Biblicus builds a context pack from structured retrieval evidence so that:
  - evidence remains a stable, testable contract
  - context formatting is explicit policy that can be changed and evaluated

  Scenario: Context pack concatenates evidence text with a join separator
    Given a retrieval result exists with evidence text:
      | text                          |
      | The user's name is Tactus.    |
      | The user's favorite color is magenta. |
    When I build a context pack from that retrieval result joining with "\n\n"
    Then the context pack text equals:
      """
      The user's name is Tactus.

      The user's favorite color is magenta.
      """

  Scenario: Context pack excludes empty evidence text
    Given a retrieval result exists with evidence text:
      | text                          |
      |                              |
      | The user's favorite color is magenta. |
      |    |
    When I build a context pack from that retrieval result joining with "\n\n"
    Then the context pack text equals:
      """
      The user's favorite color is magenta.
      """

  Scenario: Context pack excludes non-text evidence
    Given a retrieval result exists with evidence text:
      | text |
      | The user's favorite color is magenta. |
      |    |
    And the second evidence item has no text payload
    When I build a context pack from that retrieval result joining with "\n\n"
    Then the context pack text equals:
      """
      The user's favorite color is magenta.
      """
