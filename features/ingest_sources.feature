Feature: Ingesting sources (paths and uniform resource locators)
  Biblicus ingestion should accept a source reference that can be either a local path or a uniform resource locator.

  Scenario: Ingest a file via file:// uniform resource locator
    Given I initialized a corpus at "corpus"
    And a text file "hello.txt" exists with contents "hello"
    When I ingest the file uniform resource locator for "hello.txt" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item has biblicus provenance with a file source uniform resource identifier

  Scenario: Ingest a markdown file via file:// uniform resource locator
    Given I initialized a corpus at "corpus"
    And a text file "page.md" exists with contents "---\ntitle: File\n---\nbody\n"
    When I ingest the file uniform resource locator for "page.md" into corpus "corpus"
    Then the last ingest succeeds

  Scenario: Ingest a file via http:// uniform resource locator
    Given I initialized a corpus at "corpus"
    And a text file "page.md" exists with contents "---\ntitle: Web\n---\nbody\n"
    And a hypertext transfer protocol server is serving the workdir
    When I ingest the hypertext transfer protocol uniform resource locator for "page.md" into corpus "corpus"
    Then the last ingest succeeds

  Scenario: Ingest a binary file via http:// uniform resource locator
    Given I initialized a corpus at "corpus"
    And a binary file "blob.bin" exists
    And a hypertext transfer protocol server is serving the workdir
    When I ingest the hypertext transfer protocol uniform resource locator for "blob.bin" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item has a sidecar metadata file

  Scenario: Ingest a Portable Document Format file via http:// uniform resource locator
    Given I initialized a corpus at "corpus"
    And a binary file "report.pdf" exists
    And a hypertext transfer protocol server is serving the workdir
    When I ingest the hypertext transfer protocol uniform resource locator for "report.pdf" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item's sidecar includes media type "application/pdf"
