Feature: Streaming ingestion for large binary items
  Ingesting large binary files should work without requiring the entire file to be loaded into memory.
  The stored bytes should match the source bytes and the reported digest should match.

  Scenario: Ingest a large binary file and verify checksum
    Given I initialized a corpus at "corpus"
    And a binary file "large.bin" exists with size 1048576 bytes
    When I ingest the file "large.bin" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingest sha256 matches the file "large.bin"

