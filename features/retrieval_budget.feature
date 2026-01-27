Feature: Retrieval budget behavior
  Budgets enforce limits while allowing unbounded dimensions.

  Scenario: Budget treats None limits as unbounded
    When I apply a budget with no per-source or character limits
    Then the budget returns 2 evidence items
    And the budget returns evidence ranks "1,2"
