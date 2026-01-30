Feature: Extraction evaluation lab
  The extraction evaluation lab provides a deterministic walkthrough with bundled data.

  Scenario: Extraction evaluation lab reports expected metrics
    When I run the extraction evaluation lab with corpus "corpus" and dataset "dataset.json"
    Then the extraction evaluation lab dataset file exists
    And the extraction evaluation lab output file exists
    And the extraction evaluation lab metrics include coverage_present 2
    And the extraction evaluation lab metrics include coverage_empty 1
    And the extraction evaluation lab metrics include coverage_missing 0
    And the extraction evaluation lab metrics include processable_fraction 1
    And the extraction evaluation lab metrics include average_similarity 1
