Feature: Pipeline recipe edge cases
  Pipeline recipe helpers expose deterministic errors for invalid inputs.

  Scenario: Pipeline recipe helper branches are exercised
    Given I initialized a corpus at "corpus"
    When I exercise pipeline recipe edge cases
    Then the pipeline recipe edge cases succeed
