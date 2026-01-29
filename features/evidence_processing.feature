Feature: Evidence processing stages
  Retrieval produces ranked evidence. Biblicus can apply additional stages that change:
  - order (rerank)
  - inclusion (filter)

  Scenario: Rerank selects longer evidence first
    Given a retrieval result exists with evidence text:
      | text |
      | short |
      | a much longer evidence text |
    When I rerank the retrieval result evidence using "rerank-longest-text"
    Then the evidence text order is:
      | text |
      | a much longer evidence text |
      | short |

  Scenario: Filter removes evidence below a minimum score
    Given a retrieval result exists with scored evidence:
      | score | text |
      | 0.9   | keep |
      | 0.1   | drop |
    When I filter the retrieval result evidence using "filter-minimum-score" with minimum score 0.5
    Then the evidence text order is:
      | text |
      | keep |
