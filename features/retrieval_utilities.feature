Feature: Retrieval utilities
  Internal helpers should behave predictably for edge cases.

  Scenario: Scan match ignores empty tokens and selects earliest match
    When I compute a scan match span for text "bar foo" and tokens "foo,,bar,baz"
    Then the scan match span is "0..3"

  Scenario: Scan match returns none when no tokens match
    When I compute a scan match span for text "alpha" and tokens "zzz"
    Then the scan match span is "none"

  Scenario: Scan match keeps the earliest span when later matches exist
    When I compute a scan match span for text "bar foo" and tokens "bar,foo"
    Then the scan match span is "0..3"

  Scenario: Scan snippet handles empty text
    When I build a scan snippet from text "<empty>" with span "none" and max chars 10
    Then the scan snippet is "<empty>"

  Scenario: Scan snippet falls back when span is missing
    When I build a scan snippet from text "abcdef" with span "none" and max chars 3
    Then the scan snippet is "abc"

  Scenario: SQLite chunking yields multiple slices
    When I split text "abcdefghijkl" into sqlite chunks with size 5 and overlap 2
    Then the sqlite chunk count is 4

  Scenario: SQLite chunking handles empty text
    When I split text "<empty>" into sqlite chunks with size 5 and overlap 2
    Then the sqlite chunk count is 0

  Scenario: Missing run artifacts contribute zero bytes
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha apple"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
    And I delete the latest run artifacts
    And I measure the latest run artifact bytes
    Then the run artifact bytes are 0
