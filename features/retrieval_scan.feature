Feature: Retrieval with scan backend
  The scan backend performs deterministic full-text scans across markdown and text
  items without materializing external indexes.

  Scenario: Build a scan run and query for evidence
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha bravo charlie"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I query with the latest run for "bravo" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query returns evidence with stage "scan"
    And the query evidence includes the last ingested item identifier

  Scenario: Scan query respects the max_total_items budget
    Given I initialized a corpus at "corpus"
    And a text file "one.md" exists with contents "topic one"
    And a text file "two.md" exists with contents "topic two"
    When I ingest the file "one.md" into corpus "corpus"
    And I ingest the file "two.md" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I query with the latest run for "topic" and budget:
      | key                  | value |
      | max_total_items      | 1     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query evidence count is 1

  Scenario: Scan query respects the max_items_per_source budget
    Given I initialized a corpus at "corpus"
    When I ingest the text "shared term one" with title "First" and tags "a" into corpus "corpus"
    And I ingest the text "shared term two" with title "Second" and tags "b" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I query with the latest run for "shared" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 1     |
    Then the query evidence count is 1

  Scenario: Scan query respects the max_total_characters budget
    Given I initialized a corpus at "corpus"
    When I ingest the text "longtext longtext longtext longtext" with title "Long" and tags "a" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I query with the latest run for "longtext" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 1     |
      | max_items_per_source | 5     |
    Then the query evidence count is 0

  Scenario: Scan backend ignores non-text items
    Given I initialized a corpus at "corpus"
    And a binary file "blob.bin" exists
    When I ingest the file "blob.bin" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I query with the latest run for "blob" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query evidence count is 0

  Scenario: Scan handles plain text files
    Given I initialized a corpus at "corpus"
    And a text file "plain.txt" exists with contents "plain content"
    When I ingest the file "plain.txt" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I query with the latest run for "plain" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query evidence count is 1
