Feature: Command-line interface parsing
  Command-line parsing should coerce config values predictably.

  Scenario: Config pairs parse floating-point values
    When I parse config pairs:
      | pair           |
      | threshold=0.5 |
    Then the parsed config value "threshold" is float 0.5

  Scenario: Config pairs reject empty keys
    When I attempt to parse config pairs:
      | pair |
      | =1  |
    Then a config parsing error is raised
    And the config parsing error mentions "Config keys must be non-empty"

  Scenario: Config pairs preserve string values
    When I parse config pairs:
      | pair      |
      | mode=fast |
    Then the parsed config value "mode" is string "fast"

  Scenario: Step specs reject empty strings
    When I attempt to parse an empty step spec
    Then a step spec parsing error is raised
    And the step spec parsing error mentions "Step spec must be non-empty"
