Feature: Coverage harness
  Drives otherwise-unhit modules so we can reach 100% coverage without excluding files.

  Scenario: Run coverage harness
    When I run the coverage harness
    Then the coverage harness succeeds

  Scenario: Run coverage harness extended
    When I run the extended coverage harness
    Then the coverage harness succeeds

  Scenario: Exhaust coverage gaps
    Given I am in an isolated coverage workspace
    When I exhaust the remaining coverage gaps
    And I exhaust the remaining dotyaml gaps
    And I exhaust the remaining embedding gaps
    And I exhaust the remaining stt gaps
    And I exhaust the remaining core gaps
    And I exhaust the remaining migration gaps
    Then the coverage gap sweeps complete
