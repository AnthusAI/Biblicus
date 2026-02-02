Feature: Context engine full path coverage
  Context assembly should exercise helper branches for budgeting and expansion.

  Scenario: Context assembler covers allocation and expansion paths
    When I exercise context assembly helpers
    Then the helper execution completes
