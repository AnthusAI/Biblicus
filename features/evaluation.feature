Feature: Retrieval evaluation
  Evaluations score retrieval quality and system metrics using a shared dataset.

  Scenario: Evaluate a scan backend run against a tiny dataset
    Given I initialized a corpus at "corpus"
    And a text file "one.md" exists with contents "alpha apple"
    And a text file "two.md" exists with contents "beta banana"
    When I ingest the file "one.md" into corpus "corpus"
    And I ingest the file "two.md" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I create an evaluation dataset at "dataset.json" with queries:
      | query_text  | expected_item  |
      | apple       | previous_item  |
      | banana      | last_ingested  |
    And I evaluate the latest run with dataset "dataset.json" and budget:
      | key                  | value |
      | max_total_items      | 3     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the evaluation reports mean reciprocal rank 1.0

  Scenario: Evaluate using source uniform resource identifier expectations
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha apple" with title "Alpha" and tags "x" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I create a source uniform resource identifier evaluation dataset at "dataset.json" for query "apple"
    And I evaluate the latest run with dataset "dataset.json" and budget:
      | key                  | value |
      | max_total_items      | 3     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the evaluation reports hit_rate 1.0

  Scenario: Evaluate an empty dataset
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I create an empty evaluation dataset at "dataset.json"
    And I evaluate the latest run with dataset "dataset.json" and budget:
      | key                  | value |
      | max_total_items      | 3     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the evaluation reports hit_rate 0.0

  Scenario: Evaluate a run with an unmatched expectation
    Given I initialized a corpus at "corpus"
    And a text file "one.md" exists with contents "alpha apple"
    When I ingest the file "one.md" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I create an evaluation dataset at "dataset.json" with queries:
      | query_text  | expected_item |
      | apple       | missing_item  |
    And I evaluate the latest run with dataset "dataset.json" and budget:
      | key                  | value |
      | max_total_items      | 3     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the evaluation reports hit_rate 0.0
    And the evaluation reports mean reciprocal rank 0.0

  Scenario: Evaluate a full-text search run and report index size
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha apple"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
    And I create an evaluation dataset at "dataset.json" with queries:
      | query_text  | expected_item |
      | apple       | last_ingested |
    And I evaluate the latest run with dataset "dataset.json" and budget:
      | key                  | value |
      | max_total_items      | 3     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the evaluation system reports index_bytes greater than 0
