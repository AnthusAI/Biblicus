Feature: Context engine retrieval internals
  Retrieval helpers should handle cached runs with retriever mismatches.

  Scenario: Retrieval snapshot uses configuration config when latest snapshot retriever mismatches
    When I resolve a context retrieval snapshot with a mismatched latest retriever
    Then the resolved snapshot retriever equals "scan"
