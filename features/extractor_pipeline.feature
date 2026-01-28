Feature: Extractor pipeline composition
  Extractors can be composed as an explicit pipeline so different extraction approaches can be combined.
  The pipeline tries extractors in order until one produces usable text.

  Scenario: Pipeline falls through when an extractor skips an item
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" with tags "extracted" into corpus "corpus"
    And I build a "cascade" extraction run in corpus "corpus" with steps:
      | extractor_id       | config_json            |
      | pass-through-text  | {}                     |
      | metadata-text      | {}                     |
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "tags: extracted"
    And the extraction run item provenance uses extractor "metadata-text"

  Scenario: Pipeline stops after the first extractor that produces text
    Given I initialized a corpus at "corpus"
    And a text file "alpha.txt" exists with contents "alpha"
    When I ingest the file "alpha.txt" into corpus "corpus"
    And I build a "cascade" extraction run in corpus "corpus" with steps:
      | extractor_id       | config_json             |
      | pass-through-text  | {}                      |
      | metadata-text      | {}                      |
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "alpha"
    And the extraction run item provenance uses extractor "pass-through-text"

  Scenario: Pipeline treats empty text as unusable and continues
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value |
      | title | Note  |
      | tags  | x     |
    And the file "note.md" has body:
      """
      """
    When I ingest the file "note.md" into corpus "corpus"
    And I build a "cascade" extraction run in corpus "corpus" with steps:
      | extractor_id       | config_json            |
      | pass-through-text  | {}                     |
      | metadata-text      | {}                     |
    Then the extracted text for the last ingested item equals:
      """
      Note
      tags: x
      """
    And the extraction run item provenance uses extractor "metadata-text"

  Scenario: Pipeline with only pass-through extractor skips non-text items
    Given I initialized a corpus at "corpus"
    And a binary file "image.png" exists
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "cascade" extraction run in corpus "corpus" with steps:
      | extractor_id       | config_json |
      | pass-through-text  | {}          |
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: Cascade extractor cannot include itself
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction run in corpus "corpus" using extractor "cascade" with step spec "cascade"
    Then the command fails with exit code 2
    And standard error includes "Cascade extractor cannot include itself as a step"

  Scenario: Step specs are rejected when not using the cascade extractor
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction run in corpus "corpus" using extractor "pass-through-text" with step spec "pass-through-text"
    Then the command fails with exit code 2
    And standard error includes "--step is only supported for the cascade extractor"

  Scenario: Empty step spec is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction run in corpus "corpus" using extractor "cascade" with step spec "   "
    Then the command fails with exit code 2
    And standard error includes "Step spec must be non-empty"

  Scenario: Step spec without extractor identifier is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction run in corpus "corpus" using extractor "cascade" with step spec ":x=y"
    Then the command fails with exit code 2
    And standard error includes "Step spec must start with an extractor identifier"

  Scenario: Step spec with trailing colon is accepted
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "Test" and tags "a" into corpus "corpus"
    And I run "extract --extractor cascade --step pass-through-text:" in corpus "corpus"
    Then the command succeeds

  Scenario: Step spec ignores empty tokens
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "Test" and tags "a" into corpus "corpus"
    And I run "extract --extractor cascade --step metadata-text:,, " in corpus "corpus"
    Then the command succeeds

  Scenario: Step spec can pass config values to an extractor
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "Test" and tags "a" into corpus "corpus"
    And I build a "cascade" extraction run in corpus "corpus" with steps:
      | extractor_id   | config_json               |
      | metadata-text  | {"include_title": false}  |
    Then the extracted text for the last ingested item equals "tags: a"
    And the extraction run item provenance uses extractor "metadata-text"

  Scenario: Step spec without key value pairs is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction run in corpus "corpus" using extractor "cascade" with step spec "metadata-text:badtoken"
    Then the command fails with exit code 2
    And standard error includes "Step config values must be key=value"

  Scenario: Step spec with empty key is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction run in corpus "corpus" using extractor "cascade" with step spec "metadata-text:=x"
    Then the command fails with exit code 2
    And standard error includes "Step config keys must be non-empty"
