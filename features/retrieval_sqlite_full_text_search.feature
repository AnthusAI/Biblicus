Feature: Retrieval with SQLite full-text search backend
  The SQLite full-text search backend provides a practical local retrieval implementation
  with chunked indexing and full-text search.

  Scenario: Build a full-text search run and query for evidence
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha bravo charlie"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
    And I query with the latest run for "bravo" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query returns evidence with stage "full-text-search"

  Scenario: Full-text search build skips non-text items
    Given I initialized a corpus at "corpus"
    And a binary file "blob.bin" exists
    When I ingest the file "blob.bin" into corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
    Then the latest run stats include text_items 0

  Scenario: Full-text search indexes plain text files
    Given I initialized a corpus at "corpus"
    And a text file "note.txt" exists with contents "alpha beta"
    When I ingest the file "note.txt" into corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
    Then the latest run stats include text_items 1

  Scenario: Full-text search chunking emits multiple chunks
    Given I initialized a corpus at "corpus"
    And a text file "long.txt" exists with contents "abcdefghijkl"
    When I ingest the file "long.txt" into corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key                | value |
      | chunk_size         | 5     |
      | chunk_overlap      | 2     |
      | snippet_characters | 120   |
    Then the latest run stats include chunks 4

  Scenario: Full-text search rebuild replaces a stale index file
    Given I initialized a corpus at "corpus"
    And a text file "alpha.txt" exists with contents "alpha"
    When I ingest the file "alpha.txt" into corpus "corpus"
    And I rebuild a SQLite full-text search index for corpus "corpus" at ".biblicus/runs/forced.sqlite"
    Then the SQLite full-text search index file exists
