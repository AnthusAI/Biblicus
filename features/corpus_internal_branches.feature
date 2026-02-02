Feature: Corpus internal branches
  Corpus helpers should handle edge cases in storage naming and ingestion.

  Scenario: Storage filename hashes long inputs
    When I build a storage filename for a long source uri
    Then the storage filename starts with "hash-"

  Scenario: Storage filename is empty when no hints exist
    When I build a storage filename without hints
    Then the storage filename equals "<empty>"

  Scenario: Storage filename uses sanitized filename without source uri
    When I build a storage filename with filename "My Report.pdf" and no source uri
    Then the storage filename contains "My Report.pdf"

  Scenario: Storage filename namespaces source uri and filename
    When I build a storage filename with filename "report.txt" and source uri "https://example.com/report"
    Then the storage filename contains "example.com"
    And the storage filename contains "report.txt"

  Scenario: Storage filename skips empty sanitized filename
    When I build a storage filename with an empty sanitized filename and source uri "https://example.com/report"
    Then the storage filename contains "example.com"

  Scenario: Finding a source uri with empty value returns nothing
    Given I have an initialized corpus at "corpus"
    When I lookup an item by source uri "<empty>"
    Then the lookup result is empty

  Scenario: Ingest item falls back to extension when no storage filename
    Given I have an initialized corpus at "corpus"
    When I ingest bytes with no filename and no source uri and media type "application/octet-stream"
    Then the stored relpath contains the item id

  Scenario: Stream ingestion detects source uri collisions
    Given I have an initialized corpus at "corpus"
    When I stream-ingest the same source uri twice
    Then the stream ingestion error mentions "already ingested"

  Scenario: Stream ingestion falls back to extension without source uri
    Given I have an initialized corpus at "corpus"
    When I stream-ingest bytes with no filename and empty source uri and media type "application/octet-stream"
    Then the stream-ingested relpath ends with the preferred extension for "application/octet-stream"

  Scenario: Note ingestion generates a text source uri
    Given I have an initialized corpus at "corpus"
    When I ingest a note without a source uri
    Then the note source uri starts with "text:"

  Scenario: Note ingestion preserves explicit source uri
    Given I have an initialized corpus at "corpus"
    When I ingest a note with source uri "note:explicit"
    Then the note source uri equals "note:explicit"
