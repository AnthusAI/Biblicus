Feature: Extraction run lifecycle
  Extraction runs create derived artifacts under the corpus without mutating raw items.
  Runs are idempotent for the same corpus catalog and the same extraction recipe.

  Scenario: Extraction run build is idempotent for the same recipe and catalog
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I remember the last extraction run reference as "first"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    Then the last extraction run reference equals "first"

  Scenario: Extraction run build changes when the catalog changes
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I remember the last extraction run reference as "first"
    And I ingest the text "beta" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    Then the last extraction run reference does not equal "first"

  Scenario: Extraction runs can be listed and inspected
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I remember the last extraction run reference as "first"
    When I list extraction runs in corpus "corpus"
    Then the extraction run list includes "first"
    When I show extraction run "first" in corpus "corpus"
    Then the shown extraction run reference equals "first"

  Scenario: An extraction run can be deleted explicitly
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I remember the last extraction run reference as "first"
    When I delete extraction run "first" in corpus "corpus"
    Then the extraction run artifacts for "first" do not exist under the corpus

  Scenario: Extraction run list is empty for a new corpus
    Given I initialized a corpus at "corpus"
    When I list extraction runs in corpus "corpus"
    Then the extraction run list is empty

  Scenario: Extraction run list ignores invalid manifest entries
    Given I initialized a corpus at "corpus"
    And a file "corpus/.biblicus/runs/extraction/pipeline/bad/manifest.json" exists with contents:
      """
      not json
      """
    When I list extraction runs in corpus "corpus"
    Then the extraction run list does not include raw reference "pipeline:bad"

  Scenario: Extraction run list supports filtering by extractor identifier
    Given I initialized a corpus at "corpus"
    And a file "corpus/.biblicus/runs/extraction/.keep" exists with contents:
      """
      keep
      """
    When I list extraction runs for extractor "pipeline" in corpus "corpus"
    Then the extraction run list is empty

  Scenario: Extraction run list ignores non-directories and missing manifests
    Given I initialized a corpus at "corpus"
    And a file "corpus/.biblicus/runs/extraction/pipeline/not-a-directory" exists with contents:
      """
      ignore
      """
    And a file "corpus/.biblicus/runs/extraction/pipeline/no-manifest/.keep" exists with contents:
      """
      ignore
      """
    When I list extraction runs in corpus "corpus"
    Then the extraction run list does not include raw reference "pipeline:not-a-directory"
    And the extraction run list does not include raw reference "pipeline:no-manifest"

  Scenario: Showing an unknown extraction run fails cleanly
    Given I initialized a corpus at "corpus"
    When I run "extract show --run pipeline:missing" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Missing extraction run manifest"

  Scenario: Deleting an unknown extraction run fails cleanly
    Given I initialized a corpus at "corpus"
    When I run "extract delete --run pipeline:missing --confirm pipeline:missing" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Missing extraction run directory"

  Scenario: Deleting requires exact confirmation
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I remember the last extraction run reference as "first"
    When I attempt to delete extraction run "first" in corpus "corpus" with confirm "nope"
    Then the command fails with exit code 2
    And standard error includes "--confirm"
