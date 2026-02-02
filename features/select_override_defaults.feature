Feature: Selection override defaults
  Selection override configs should supply default media type patterns.

  Scenario: SelectOverrideConfig defaults to all media types
    When I build a SelectOverride config with defaults
    Then the override media type patterns equal:
      | pattern |
      | */*     |

  Scenario: SelectSmartOverrideConfig defaults to all media types
    When I build a SelectSmartOverride config with defaults
    Then the override media type patterns equal:
      | pattern |
      | */*     |
