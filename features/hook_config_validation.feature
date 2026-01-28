Feature: Hook configuration validation
  Hook specifications are validated strictly at corpus open time.
  Invalid hook configuration must fail with a clear error.

  Scenario: Unknown hook identifier fails
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" config includes hooks JavaScript Object Notation:
      """
      [
        {"hook_id": "unknown-hook", "hook_points": ["after_ingest"], "config": {}}
      ]
      """
    When I ingest the text "hello" with title "Test" and tags "a" into corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unknown hook_id"

  Scenario: Invalid hook specification fails
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" config includes hooks JavaScript Object Notation:
      """
      [
        {"hook_points": ["after_ingest"], "config": {}}
      ]
      """
    When I ingest the text "hello" with title "Test" and tags "a" into corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Invalid hook specification"

