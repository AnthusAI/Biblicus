Feature: Domain model validation
  Biblicus models must reject invalid structures.

  Scenario: Evidence requires text or content reference
    When I attempt to create evidence without text or content reference
    Then a model validation error is raised
