Feature: Context engine retrieval internals
  Retrieval helpers should handle cached runs with backend mismatches.

  Scenario: Retrieval run uses recipe config when latest run backend mismatches
    When I resolve a context retrieval run with a mismatched latest backend
    Then the resolved run backend equals "scan"
