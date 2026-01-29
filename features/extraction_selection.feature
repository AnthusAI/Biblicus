Feature: Pipeline selection
  Selection extractors can choose among prior pipeline outputs for each item.

  Scenario: Selection extractor chooses the first usable prior output in pipeline order
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value |
      | title | Note  |
      | tags  | a     |
    And the file "note.md" has body:
      """
      body
      """
    When I ingest the file "note.md" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id       | config_json |
      | metadata-text      | {}          |
      | pass-through-text  | {}          |
      | select-text        | {}          |
    Then the extracted text for the last ingested item equals:
      """
      Note
      tags: a
      """
    And the extraction run item provenance uses extractor "metadata-text"

  Scenario: Selection extractor skips empty outputs and chooses a later usable output
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value |
      | title | Note  |
      | tags  | a     |
    And the file "note.md" has body:
      """
      """
    When I ingest the file "note.md" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id       | config_json |
      | pass-through-text  | {}          |
      | metadata-text      | {}          |
      | select-text        | {}          |
    Then the extracted text for the last ingested item equals:
      """
      Note
      tags: a
      """
    And the extraction run item provenance uses extractor "metadata-text"

  Scenario: Selection extractor produces no output when no prior outputs exist
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id  | config_json |
      | select-text   | {}          |
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: Selection extractor preserves empty output when no usable output exists
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value |
      | title | Note  |
    And the file "note.md" has body:
      """
      """
    When I ingest the file "note.md" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id       | config_json |
      | pass-through-text  | {}          |
      | select-text        | {}          |
    Then the extracted text for the last ingested item is empty
    And the extraction run item provenance uses extractor "pass-through-text"
