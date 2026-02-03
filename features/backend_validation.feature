Feature: Retriever guardrails
  Retriever prerequisites are validated explicitly.

  Scenario: SQLite full-text search version five requirement is enforced
    When I check full-text search version five availability against a failing connection
    Then a retriever prerequisite error is raised

  Scenario: SQLite retriever requires artifacts
    When I attempt to resolve a snapshot without artifacts
    Then a retriever artifact error is raised

  Scenario: Abstract retriever methods raise NotImplementedError
    When I call the abstract retriever methods
    Then the abstract retriever errors are raised
