Feature: Text extraction runs
  Text extraction is a separate, pluggable pipeline stage that produces derived text artifacts.
  Extracted text artifacts are stored under the corpus and can coexist for multiple pipeline runs.

  Scenario: Build an extraction run that writes per-item text artifacts
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" with tags "extracted from binary" into corpus "corpus"
    And I build a "metadata-text" extraction run in corpus "corpus"
    Then the extraction run artifacts exist under the corpus for extractor "pipeline"
    And the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "tags: extracted from binary"
    And the extraction run stats include total_items 1
    And the extraction run stats include needs_extraction_items 1
    And the extraction run stats include converted_items 1

  Scenario: Extraction artifacts are retained for multiple pipeline runs
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" with tags "retained" into corpus "corpus"
    And I build a "metadata-text" extraction run in corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    Then the corpus has at least 2 extraction runs for extractor "pipeline"

  Scenario: Empty extracted text is recorded as empty output
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value |
      | title | Note  |
    And the file "note.md" has body:
      """
      """
    When I ingest the file "note.md" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item is empty
    And the extraction run stats include extracted_empty_items 1
    And the extraction run stats include extracted_nonempty_items 0
    And the extraction run stats include converted_items 0

  Scenario: Pass-through text extractor skips non-text items
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    Then the extraction run artifacts exist under the corpus for extractor "pipeline"
    And the extraction run does not include extracted text for the last ingested item
    And the extraction run stats include converted_items 0

  Scenario: Pass-through text extractor extracts text items
    Given I initialized a corpus at "corpus"
    And a text file "alpha.txt" exists with contents "alpha"
    When I ingest the file "alpha.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    Then the extraction run artifacts exist under the corpus for extractor "pipeline"
    And the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "alpha"

  Scenario: Pass-through text extractor extracts markdown items
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value |
      | title | Note  |
    And the file "note.md" has body:
      """
      body line
      """
    When I ingest the file "note.md" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "body line"

  Scenario: Metadata text extractor skips items with no title or tags
    Given I initialized a corpus at "corpus"
    And a text file "alpha.txt" exists with contents "alpha"
    When I ingest the file "alpha.txt" into corpus "corpus"
    And I build a "metadata-text" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item
    And the extraction run stats include converted_items 0

  Scenario: Unknown extractor is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build a "unknown" extraction run in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unknown extractor"
