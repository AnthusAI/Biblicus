Feature: Springstack explorer navigation
  Scenario: Navigate from root to corpus and item
    Given the explorer is open
    When I open the first corpus
    Then the URL includes the corpus
    When I open the first item
    Then the URL includes the item

  Scenario: Navigate using breadcrumbs
    Given the explorer is open
    When I open the first corpus
    And I open the first item
    When I click the root breadcrumb
    Then I should be at the root level

  Scenario: Deep link loads the correct stack
    Given the explorer is open
    And I capture the first corpus and item ids
    When I visit the item deep link
    Then the URL includes the item

  Scenario: Toggle data mode updates root label
    Given the explorer is open
    When I toggle the data mode
    Then the root breadcrumb label changes
