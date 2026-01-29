Feature: Portable Document Format text extraction
  Portable Document Format items can produce derived text artifacts through an extraction plugin.
  The raw Portable Document Format bytes remain unchanged in the corpus raw directory.

  Scenario: Portable Document Format text extractor produces text artifacts
    Given I initialized a corpus at "corpus"
    And a Portable Document Format file "hello.pdf" exists with text "Hello from Portable Document Format"
    When I ingest the file "hello.pdf" into corpus "corpus"
    And I build a "pdf-text" extraction run in corpus "corpus"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "Hello from Portable Document Format"
    And the extraction run item provenance uses extractor "pdf-text"
    And the extraction run stats include needs_extraction_items 1
    And the extraction run stats include converted_items 1

  Scenario: Portable Document Format text extractor skips non Portable Document Format items
    Given I initialized a corpus at "corpus"
    And a text file "alpha.txt" exists with contents "alpha"
    When I ingest the file "alpha.txt" into corpus "corpus"
    And I build a "pdf-text" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item
    And the extraction run stats include converted_items 0

  Scenario: Portable Document Format text extractor supports a maximum page limit
    Given I initialized a corpus at "corpus"
    And a Portable Document Format file "hello.pdf" exists with text "Hello from Portable Document Format"
    When I ingest the file "hello.pdf" into corpus "corpus"
    And I build a "pdf-text" extraction run in corpus "corpus" with config:
      | key       | value |
      | max_pages | 1     |
    Then the extracted text for the last ingested item equals "Hello from Portable Document Format"

  Scenario: Portable Document Format text extractor records empty output when no text is extractable
    Given I initialized a corpus at "corpus"
    And a Portable Document Format file "scan.pdf" exists with no extractable text
    When I ingest the file "scan.pdf" into corpus "corpus"
    And I build a "pdf-text" extraction run in corpus "corpus"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item is empty
    And the extraction run stats include extracted_empty_items 1
    And the extraction run stats include converted_items 0
