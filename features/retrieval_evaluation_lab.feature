Feature: Retrieval evaluation lab
  The retrieval evaluation lab provides a deterministic walkthrough with bundled data.

  Scenario: Retrieval evaluation lab reports expected metrics
    When I snapshot the retrieval evaluation lab with corpus "corpus" and dataset "dataset.json"
    Then the retrieval evaluation lab dataset file exists
    And the retrieval evaluation lab output file exists
    And the retrieval evaluation lab metrics include hit_rate 1
    And the retrieval evaluation lab metrics include mean_reciprocal_rank 1
    And the retrieval evaluation lab metrics include precision_at_max_total_items 0.3333333333333333
