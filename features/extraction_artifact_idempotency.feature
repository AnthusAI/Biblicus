Feature: Extraction artifact idempotency
  Extraction artifacts are written once per item and reused across repeated runs.

  Scenario: Rebuilding an extraction snapshot does not rewrite extracted artifacts
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "Doc" and tags "alpha" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I record the extracted text timestamp for the item tagged "alpha"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    Then the extracted text timestamp for the item tagged "alpha" is unchanged

  Scenario: Forcing extraction rewrites extracted artifacts
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "Doc" and tags "alpha" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I record the extracted text timestamp for the item tagged "alpha"
    And I wait for 1.1 seconds
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages and force:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    Then the extracted text timestamp for the item tagged "alpha" is updated

  Scenario: Missing final artifacts are rebuilt from cached stages
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "Doc" and tags "alpha" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I delete extracted artifacts for the item tagged "alpha"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    Then the extraction snapshot includes extracted text for the item tagged "alpha"

  Scenario: Extraction can run with multiple workers
    Given I initialized a corpus at "corpus"
    And I ingested note items into corpus "corpus":
      | text  |
      | alpha |
      | beta  |
    When I build a "pipeline" extraction snapshot in corpus "corpus" with stages and max workers 2:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    Then the extraction snapshot includes extracted text for all items
