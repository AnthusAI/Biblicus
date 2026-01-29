Feature: Longest text selection
  The longest text selection extractor can choose among prior pipeline outputs for each item.

  Scenario: Longest selection chooses the longest usable prior output
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value |
      | title | Note  |
      | tags  | a     |
    And the file "note.md" has body:
      """
      body body body
      """
    When I ingest the file "note.md" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id         | config_json |
      | metadata-text        | {}          |
      | pass-through-text    | {}          |
      | select-longest-text  | {}          |
    Then the extracted text for the last ingested item equals:
      """
      body body body
      """
    And the extraction run item provenance uses extractor "pass-through-text"

  Scenario: Longest selection chooses the earliest step when there is a length tie
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value |
      | title | Note  |
    And the file "note.md" has body:
      """
      alpha
      """
    When I ingest the file "note.md" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id         | config_json |
      | pass-through-text    | {}          |
      | pass-through-text    | {}          |
      | select-longest-text  | {}          |
    Then the extracted text for the last ingested item equals "alpha"

  Scenario: Longest selection produces no output when no prior outputs exist
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id         | config_json |
      | select-longest-text  | {}          |
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: Longest selection preserves empty output when no usable output exists
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value |
      | title | Note  |
    And the file "note.md" has body:
      """
      """
    When I ingest the file "note.md" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id         | config_json |
      | pass-through-text    | {}          |
      | select-longest-text  | {}          |
    Then the extracted text for the last ingested item is empty
    And the extraction run item provenance uses extractor "pass-through-text"
