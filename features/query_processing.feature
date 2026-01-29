Feature: Query processing stages
  The query command can apply evidence processing stages after retrieval.

  Scenario: Query can rerank evidence by text length
    Given I initialized a corpus at "corpus"
    And I ingested note items into corpus "corpus":
      | text |
      | short evidence |
      | a much longer evidence text |
    And I built a scan run for corpus "corpus"
    When I query corpus "corpus" with query "evidence" reranking with "rerank-longest-text"
    Then the query result evidence text order is:
      | text |
      | a much longer evidence text |
      | short evidence |

  Scenario: Query can filter evidence by minimum score
    Given I initialized a corpus at "corpus"
    And I ingested note items into corpus "corpus":
      | text |
      | keep keep |
      | keep |
    And I built a scan run for corpus "corpus"
    When I query corpus "corpus" with query "keep" filtering with minimum score 2.0
    Then the query result evidence text order is:
      | text |
      | keep keep |
