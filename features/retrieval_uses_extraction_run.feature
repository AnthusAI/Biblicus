Feature: Retrieval can use extracted text artifacts
  Retrieval backends can build and query using a selected extraction run.
  This allows extraction plugins and retrieval plugins to be combined independently.

  Scenario: Query finds text extracted from a Portable Document Format item
    Given I initialized a corpus at "corpus"
    And a Portable Document Format file "hello.pdf" exists with text "Portable Document Format retrieval"
    When I ingest the file "hello.pdf" into corpus "corpus"
    And I build a "pdf-text" extraction run in corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
    And I query with the latest run for "Portable Document Format retrieval" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | max_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence includes the last ingested item identifier

  Scenario: Query finds text that exists only in extracted artifacts
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" with tags "unique extracted phrase" into corpus "corpus"
    And I build a "metadata-text" extraction run in corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                  | value |
      | chunk_size           | 200   |
      | chunk_overlap        | 50    |
      | snippet_characters   | 120   |
    And I query with the latest run for "unique extracted phrase" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | max_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence includes the last ingested item identifier

  Scenario: Retrieval build fails when the extraction run does not exist
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I attempt to build a "sqlite-full-text-search" retrieval run in corpus "corpus" with extraction run "metadata-text:missing"
    Then the command fails with exit code 2
    And standard error includes "Missing extraction run"

  Scenario: Scan backend can query using extracted text artifacts
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" with tags "scan extracted phrase" into corpus "corpus"
    And I build a "metadata-text" extraction run in corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                | value |
      | snippet_characters | 120   |
    And I query with the latest run for "scan extracted phrase" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | max_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence includes the last ingested item identifier

  Scenario: Invalid extraction run reference is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build a "sqlite-full-text-search" retrieval run in corpus "corpus" with extraction run "invalid"
    Then the command fails with exit code 2
    And standard error includes "Extraction run reference must be extractor_id:run_id"

  Scenario: Extraction run reference requires non-empty parts
    Given I initialized a corpus at "corpus"
    When I attempt to build a "sqlite-full-text-search" retrieval run in corpus "corpus" with extraction run "x:"
    Then the command fails with exit code 2
    And standard error includes "non-empty parts"

  Scenario: Scan backend rejects a missing extraction run
    Given I initialized a corpus at "corpus"
    When I attempt to build a "scan" retrieval run in corpus "corpus" with extraction run "metadata-text:missing"
    Then the command fails with exit code 2
    And standard error includes "Missing extraction run"

  Scenario: Skipped extraction artifacts do not produce evidence
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                | value |
      | snippet_characters | 120   |
    And I query with the latest run for "anything" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | max_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence count is 0

  Scenario: SQLite full-text search ignores items with no extracted text artifacts
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
    And I query with the latest run for "anything" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | max_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence count is 0
