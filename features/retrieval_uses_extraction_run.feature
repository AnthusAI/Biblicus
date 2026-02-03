Feature: Retrieval can use extracted text artifacts
  Retrieval backends can build and query using a selected extraction snapshot.
  This allows extraction plugins and retrieval plugins to be combined independently.

  Scenario: Query finds text extracted from a Portable Document Format item
    Given I initialized a corpus at "corpus"
    And a Portable Document Format file "hello.pdf" exists with text "Portable Document Format retrieval"
    When I ingest the file "hello.pdf" into corpus "corpus"
    And I build a "pdf-text" extraction snapshot in corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
    And I query with the latest snapshot for "Portable Document Format retrieval" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | maximum_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence includes the last ingested item identifier

  Scenario: Query finds text that exists only in extracted artifacts
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" with tags "unique extracted phrase" into corpus "corpus"
    And I build a "metadata-text" extraction snapshot in corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key                  | value |
      | chunk_size           | 200   |
      | chunk_overlap        | 50    |
      | snippet_characters   | 120   |
    And I query with the latest snapshot for "unique extracted phrase" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | maximum_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence includes the last ingested item identifier

  Scenario: Retrieval build fails when the extraction snapshot does not exist
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I attempt to build a "sqlite-full-text-search" retrieval snapshot in corpus "corpus" with extraction snapshot "metadata-text:missing"
    Then the command fails with exit code 2
    And standard error includes "Missing extraction snapshot"

  Scenario: Scan retriever can query using extracted text artifacts
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" with tags "scan extracted phrase" into corpus "corpus"
    And I build a "metadata-text" extraction snapshot in corpus "corpus"
    And I build a "scan" retrieval snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key                | value |
      | snippet_characters | 120   |
    And I query with the latest snapshot for "scan extracted phrase" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | maximum_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence includes the last ingested item identifier

  Scenario: Invalid extraction snapshot reference is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build a "sqlite-full-text-search" retrieval snapshot in corpus "corpus" with extraction snapshot "invalid"
    Then the command fails with exit code 2
    And standard error includes "Extraction snapshot reference must be extractor_id:snapshot_id"

  Scenario: Extraction snapshot reference requires non-empty parts
    Given I initialized a corpus at "corpus"
    When I attempt to build a "sqlite-full-text-search" retrieval snapshot in corpus "corpus" with extraction snapshot "x:"
    Then the command fails with exit code 2
    And standard error includes "non-empty parts"

  Scenario: Scan retriever rejects a missing extraction snapshot
    Given I initialized a corpus at "corpus"
    When I attempt to build a "scan" retrieval snapshot in corpus "corpus" with extraction snapshot "metadata-text:missing"
    Then the command fails with exit code 2
    And standard error includes "Missing extraction snapshot"

  Scenario: Skipped extraction artifacts do not produce evidence
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pass-through-text" extraction snapshot in corpus "corpus"
    And I build a "scan" retrieval snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key                | value |
      | snippet_characters | 120   |
    And I query with the latest snapshot for "anything" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | maximum_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence count is 0

  Scenario: SQLite full-text search ignores items with no extracted text artifacts
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pass-through-text" extraction snapshot in corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
    And I query with the latest snapshot for "anything" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | maximum_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence count is 0
