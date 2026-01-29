Feature: Unstructured extractor plugin
  The Unstructured extractor provides broad document text extraction as an optional dependency.
  It is intended as a last-resort extractor for non-text items that need derived text.

  Scenario: Unstructured extractor requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the Unstructured dependency is unavailable
    And a Portable Document Format file "hello.pdf" exists with text "Hello"
    When I ingest the file "hello.pdf" into corpus "corpus"
    And I attempt to build a "unstructured" extraction run in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[unstructured]"

  Scenario: Unstructured extractor skips text items
    Given I initialized a corpus at "corpus"
    And a fake Unstructured library is available
    When I ingest the text "alpha" with title "Alpha" and tags "a" into corpus "corpus"
    And I build a "unstructured" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: Unstructured extractor produces extracted text for a non-text item
    Given I initialized a corpus at "corpus"
    And a fake Unstructured library is available that returns text "Extracted by Unstructured" for filename "doc.pdf"
    And a binary file "doc.pdf" exists
    When I ingest the file "doc.pdf" into corpus "corpus"
    And I build a "unstructured" extraction run in corpus "corpus"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "Extracted by Unstructured"
    And the extraction run item provenance uses extractor "unstructured"

  Scenario: Unstructured extractor records empty output when it cannot extract text
    Given I initialized a corpus at "corpus"
    And a fake Unstructured library is available that returns empty output for filename "empty.pdf"
    And a binary file "empty.pdf" exists
    When I ingest the file "empty.pdf" into corpus "corpus"
    And I build a "unstructured" extraction run in corpus "corpus"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item is empty
    And the extraction run stats include extracted_empty_items 1

  Scenario: Unstructured extractor ignores whitespace element output
    Given I initialized a corpus at "corpus"
    And a fake Unstructured library is available that returns whitespace output for filename "whitespace.pdf"
    And a binary file "whitespace.pdf" exists
    When I ingest the file "whitespace.pdf" into corpus "corpus"
    And I build a "unstructured" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item is empty
    And the extraction run stats include extracted_empty_items 1

  Scenario: Unstructured extractor records per-item errors and continues
    Given I initialized a corpus at "corpus"
    And a fake Unstructured library is available that raises a RuntimeError for filename "boom.pdf"
    And a binary file "boom.pdf" exists
    And a fake Unstructured library is available that returns text "ok" for filename "ok.pdf"
    And a binary file "ok.pdf" exists
    When I ingest the file "boom.pdf" into corpus "corpus"
    And I ingest the file "ok.pdf" into corpus "corpus"
    And I build a "unstructured" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "ok"
    And the extraction run includes an errored result for the first ingested item
    And the extraction run error type for the first ingested item equals "RuntimeError"
    And the extraction run stats include errored_items 1
