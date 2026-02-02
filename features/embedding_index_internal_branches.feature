Feature: Embedding index snippet helpers
  Embedding index helpers must return deterministic snippet text for evidence.

  Scenario: Span extraction returns None for non-text
    When I extract span text from non-text with span 0 1
    Then the snippet result is None

  Scenario: Span extraction returns full text for invalid span
    When I extract span text from "alpha" with span -1 0
    Then the snippet result equals "alpha"

  Scenario: Snippet builder returns None for non-text
    When I build a snippet from non-text with span 0 1 and max chars 10
    Then the snippet result is None

  Scenario: Snippet builder returns empty string for non-positive max chars
    When I build a snippet from "alpha" with span 0 1 and max chars 0
    Then the snippet result equals "<empty>"

  Scenario: Snippet builder falls back to leading text for invalid span
    When I build a snippet from "alpha beta" with span -1 0 and max chars 5
    Then the snippet result equals "alpha"
