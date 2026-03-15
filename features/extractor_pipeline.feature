Feature: Extraction pipeline
  Extractors are composed as an explicit pipeline where each stage can see the outputs of prior stages.
  The final extracted text is the last extracted output in pipeline order.

  Scenario: Pipeline final output comes from the last extracted stage
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
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json |
      | pass-through-text  | {}          |
      | metadata-text      | {}          |
    Then the extracted text for the last ingested item equals:
      """
      Note
      tags: a
      """
    And the extraction snapshot item provenance uses extractor "metadata-text"

  Scenario: Selection stage can choose an earlier output
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
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json |
      | pass-through-text  | {}          |
      | metadata-text      | {}          |
      | select-text        | {}          |
    Then the extracted text for the last ingested item equals "body"
    And the extraction snapshot item provenance uses extractor "pass-through-text"

  Scenario: Pipeline rejects stages that include the pipeline extractor
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction snapshot in corpus "corpus" using extractor "pipeline" with stage spec "pipeline"
    Then the command fails with exit code 2
    And standard error includes "Pipeline stages cannot include the pipeline extractor itself"

  Scenario: Pipeline requires at least one stage
    Given I initialized a corpus at "corpus"
    When I snapshot "extract build" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Pipeline extraction requires at least one --stage"

  Scenario: Stage spec without extractor identifier is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction snapshot in corpus "corpus" using extractor "pipeline" with stage spec ":x=y"
    Then the command fails with exit code 2
    And standard error includes "Stage spec must start with an extractor identifier"

  Scenario: Stage spec with trailing colon is accepted
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "Test" and tags "a" into corpus "corpus"
    And I snapshot "extract build --stage pass-through-text:" in corpus "corpus"
    Then the command succeeds

  Scenario: Stage spec ignores empty tokens
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "Test" and tags "a" into corpus "corpus"
    And I snapshot "extract build --stage metadata-text:,, " in corpus "corpus"
    Then the command succeeds

  Scenario: Stage spec can pass config values to an extractor
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "Test" and tags "a" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id   | config_json               |
      | metadata-text  | {"include_title": false}  |
    Then the extracted text for the last ingested item equals "tags: a"
    And the extraction snapshot item provenance uses extractor "metadata-text"

  Scenario: Stage spec without key value pairs is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction snapshot in corpus "corpus" using extractor "pipeline" with stage spec "metadata-text:badtoken"
    Then the command fails with exit code 2
    And standard error includes "Config values must be key=value"

  Scenario: Stage spec with empty key is rejected
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction snapshot in corpus "corpus" using extractor "pipeline" with stage spec "metadata-text:=x"
    Then the command fails with exit code 2
    And standard error includes "Config keys must be non-empty"

  Scenario: Pipeline extractor cannot be executed directly
    When I call the pipeline extractor directly
    Then the pipeline extractor raises a fatal extraction error

  Scenario: Extraction runs require the pipeline extractor
    Given I initialized a corpus at "corpus"
    When I attempt to build a non-pipeline extraction snapshot in corpus "corpus"
    Then a fatal extraction error is raised
    And the fatal extraction error message includes "Extraction snapshots must use the pipeline extractor"
