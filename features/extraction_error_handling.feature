Feature: Extraction error handling
  An extraction run should continue when an extractor fails for a single item.
  Failures are recorded per item so operators can understand what happened and decide how to respond.

  Scenario: Extraction continues and records an error when an item has invalid text encoding
    Given I initialized a corpus at "corpus"
    And a text file "good.txt" exists with contents "good"
    And a binary file "bad.txt" exists with invalid Unicode Transformation Format 8 bytes
    When I ingest the file "bad.txt" into corpus "corpus"
    And I ingest the file "good.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "good"
    And the extraction run includes an errored result for the first ingested item
    And the extraction run error type for the first ingested item equals "UnicodeDecodeError"
    And the extraction run stats include errored_items 1

  Scenario: Errored items do not create extracted text artifacts
    Given I initialized a corpus at "corpus"
    And a binary file "bad.txt" exists with invalid Unicode Transformation Format 8 bytes
    When I ingest the file "bad.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item
    And the extraction run includes an errored result for the last ingested item

  Scenario: Extraction aborts on fatal extractor errors
    Given I initialized a corpus at "corpus"
    And a text file "alpha.txt" exists with contents "alpha"
    When I ingest the file "alpha.txt" into corpus "corpus"
    And I attempt to build a pipeline extraction run in corpus "corpus" with a fatal extractor step
    Then a fatal extraction error is raised
    And the fatal extraction error message includes "Fatal extractor failure"
