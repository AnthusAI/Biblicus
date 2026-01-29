Feature: Context pack command-line interface
  The command-line interface can build a context pack from a retrieval result.
  This allows a Unix style workflow where retrieval output is piped into context building.

  Scenario: Context pack build reads retrieval result from standard input
    Given a retrieval result exists with evidence text:
      | text |
      | The user's favorite color is magenta. |
    When I run "context-pack build" joining with "\n\n"
    Then the context pack build output text equals:
      """
      The user's favorite color is magenta.
      """

  Scenario: Context pack build can fit to a token budget
    Given a retrieval result exists with evidence text:
      | text |
      | one two three |
      | four five six |
    When I run "context-pack build" joining with "\n\n" and token budget 3
    Then the context pack build output text equals:
      """
      one two three
      """

  Scenario: Context pack build fails without retrieval result on standard input
    When I run "context-pack build" with empty standard input
    Then the command fails with exit code 2
    And standard error includes "Context pack build requires a retrieval result"
