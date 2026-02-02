Feature: TF vector snippet helpers
  TF vector helpers should respect snippet limits.

  Scenario: TF vector snippet returns empty when max chars is non-positive
    When I build a TF vector snippet for "alpha" with no span and max chars 0
    Then the TF vector snippet equals "<empty>"

  Scenario: TF vector snippet returns prefix when span is missing
    When I build a TF vector snippet for "alpha beta" with no span and max chars 5
    Then the TF vector snippet equals "alpha"
