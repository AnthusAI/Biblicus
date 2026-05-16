Feature: Text extraction snapshots
  Text extraction is a separate, pluggable pipeline stage that produces derived text artifacts.
  Extracted text artifacts are stored under the corpus and can coexist for multiple pipeline runs.

  Scenario: Build an extraction snapshot that writes per-item text artifacts
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" with tags "extracted from binary" into corpus "corpus"
    And I build a "metadata-text" extraction snapshot in corpus "corpus"
    Then the extraction snapshot artifacts exist under the corpus for extractor "pipeline"
    And the extraction snapshot includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "tags: extracted from binary"
    And the extraction snapshot stats include total_items 1
    And the extraction snapshot stats include needs_extraction_items 1
    And the extraction snapshot stats include converted_items 1

  Scenario: Extraction artifacts are retained for multiple pipeline runs
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" with tags "retained" into corpus "corpus"
    And I build a "metadata-text" extraction snapshot in corpus "corpus"
    And I build a "pass-through-text" extraction snapshot in corpus "corpus"
    Then the corpus has at least 2 extraction snapshots for extractor "pipeline"

  Scenario: Empty extracted text is recorded as empty output
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value |
      | title | Note  |
    And the file "note.md" has body:
      """
      """
    When I ingest the file "note.md" into corpus "corpus"
    And I build a "pass-through-text" extraction snapshot in corpus "corpus"
    Then the extraction snapshot includes extracted text for the last ingested item
    And the extracted text for the last ingested item is empty
    And the extraction snapshot stats include extracted_empty_items 1
    And the extraction snapshot stats include extracted_nonempty_items 0
    And the extraction snapshot stats include converted_items 0

  Scenario: Pass-through text extractor skips non-text items
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pass-through-text" extraction snapshot in corpus "corpus"
    Then the extraction snapshot artifacts exist under the corpus for extractor "pipeline"
    And the extraction snapshot does not include extracted text for the last ingested item
    And the extraction snapshot stats include converted_items 0

  Scenario: Pass-through text extractor extracts text items
    Given I initialized a corpus at "corpus"
    And a text file "alpha.txt" exists with contents "alpha"
    When I ingest the file "alpha.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction snapshot in corpus "corpus"
    Then the extraction snapshot artifacts exist under the corpus for extractor "pipeline"
    And the extraction snapshot includes extracted text for the last ingested item
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
    And I build a "pass-through-text" extraction snapshot in corpus "corpus"
    Then the extraction snapshot includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "body line"

  Scenario: Metadata text extractor skips items with no title or tags
    Given I initialized a corpus at "corpus"
    And a text file "alpha.txt" exists with contents "alpha"
    When I ingest the file "alpha.txt" into corpus "corpus"
    And I build a "metadata-text" extraction snapshot in corpus "corpus"
    Then the extraction snapshot does not include extracted text for the last ingested item
    And the extraction snapshot stats include converted_items 0

  Scenario: Metadata text extractor emits selected fields without candidate-label leakage
    Given I initialized a corpus at "corpus"
    And a text file "paper.txt" exists with contents "full text should not be used"
    And a metadata file "paper.metadata.yml" exists with:
      """
      title: Contrastive Agents
      abstract: A study of agent memory and tool-use evaluation.
      tags:
        - blind-candidate
      curation:
        proposed_topic_uid: leaked-topic
      """
    When I standard-ingest the file "paper.txt" into corpus "corpus" with metadata file "paper.metadata.yml" and source uniform resource identifier "urn:test:paper"
    And I build a "metadata-text" extraction snapshot in corpus "corpus" with config:
      | key    | value                     |
      | fields | ["title","metadata.abstract"] |
    Then the extracted text for the last ingested item equals:
      """
      Contrastive Agents
      A study of agent memory and tool-use evaluation.
      """
    And the extracted text for the last ingested item does not contain "blind-candidate"
    And the extracted text for the last ingested item does not contain "leaked-topic"

  Scenario: Unknown extractor is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build a "unknown" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unknown extractor"
