@integration
Feature: Portable Document Format extraction and retrieval integration
  Real Portable Document Format files can be downloaded, extracted, indexed, and queried in one flow.

  Scenario: Query finds text extracted from a downloaded Portable Document Format
    Given I initialized a corpus at "corpus"
    When I ingest the uniform resource locator "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf" into corpus "corpus"
    And I build a "pdf-text" extraction run in corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
    And I query with the latest run for "Dummy PDF file" and budget:
      | key                 | value |
      | max_total_items     | 5     |
      | max_total_characters| 10000 |
      | max_items_per_source| 5     |
    Then the query evidence includes the last ingested item identifier

