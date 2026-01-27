Feature: Backend guardrails
  Backend prerequisites are validated explicitly.

  Scenario: SQLite full-text search version five requirement is enforced
    When I check full-text search version five availability against a failing connection
    Then a backend prerequisite error is raised

  Scenario: SQLite backend requires artifacts
    When I attempt to resolve a run without artifacts
    Then a backend artifact error is raised

  Scenario: Abstract backend methods raise NotImplementedError
    When I call the abstract backend methods
    Then the abstract backend errors are raised
