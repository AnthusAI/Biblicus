Feature: Configuration utilities
  Configuration composition and override helpers are strict and predictable.

  Scenario: Override parsing supports booleans, numbers, null, and JSON arrays
    When I parse override values:
      | raw   | expected_json |
      | true  | true          |
      | false | false         |
      | 12    | 12            |
      | 1.25  | 1.25          |
      | null  | null          |
      | [1,2] | [1,2]         |
    Then the parsed override values match the expected JSON

  Scenario: Override parsing preserves empty strings and non-numeric scalars
    When I parse override values:
      | raw    | expected_json |
      |        | ""            |
      | abc    | "abc"         |
    Then the parsed override values match the expected JSON

  Scenario: Invalid JSON override values are treated as literal strings
    When I parse override values:
      | raw          | expected_json |
      | [not json    | "[not json"   |
    Then the parsed override values match the expected JSON

  Scenario: Dotted overrides update nested mappings
    Given a base config mapping exists:
      """
      {"a": {"b": 1}}
      """
    When I apply dotted overrides:
      | key | value |
      | a.c | 2     |
    Then the updated config JSON equals:
      """
      {"a": {"b": 1, "c": 2}}
      """

  Scenario: Dotted overrides replace non-mapping intermediate values
    Given a base config mapping exists:
      """
      {"a": 1}
      """
    When I apply dotted overrides:
      | key | value |
      | a.b | 2     |
    Then the updated config JSON equals:
      """
      {"a": {"b": 2}}
      """

  Scenario: Dotted override parsing rejects malformed pairs
    When I attempt to parse dotted overrides:
      | pair |
      | abc  |
    Then a ValueError is raised
    And the ValueError message includes "key=value"

  Scenario: Dotted override parsing rejects empty keys
    When I attempt to parse dotted overrides:
      | pair |
      | =1   |
    Then a ValueError is raised
    And the ValueError message includes "non-empty"

  Scenario: Applying dotted overrides rejects empty dotted keys
    Given a base config mapping exists:
      """
      {"a": 1}
      """
    When I attempt to apply dotted overrides:
      | key | value |
      | .   | 1     |
    Then a ValueError is raised
    And the ValueError message includes "non-empty"
