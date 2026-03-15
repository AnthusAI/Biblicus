Feature: Extraction snapshot lifecycle
  Extraction snapshots create derived artifacts under the corpus without mutating raw items.
  Snapshots are idempotent for the same corpus catalog and the same extraction configuration.

  Scenario: Extraction snapshot build is idempotent for the same configuration and catalog
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I remember the last extraction snapshot reference as "first"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    Then the last extraction snapshot reference equals "first"

  Scenario: Extraction snapshot build changes when the catalog changes
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I remember the last extraction snapshot reference as "first"
    And I ingest the text "beta" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    Then the last extraction snapshot reference does not equal "first"

  Scenario: Extraction snapshots can be listed and inspected
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I remember the last extraction snapshot reference as "first"
    When I list extraction snapshots in corpus "corpus"
    Then the extraction snapshot list includes "first"
    When I show extraction snapshot "first" in corpus "corpus"
    Then the shown extraction snapshot reference equals "first"

  Scenario: An extraction snapshot can be deleted explicitly
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I remember the last extraction snapshot reference as "first"
    When I delete extraction snapshot "first" in corpus "corpus"
    Then the extraction snapshot artifacts for "first" do not exist under the corpus

  Scenario: Extraction snapshot list is empty for a new corpus
    Given I initialized a corpus at "corpus"
    When I list extraction snapshots in corpus "corpus"
    Then the extraction snapshot list is empty

  Scenario: Extraction snapshot list ignores invalid manifest entries
    Given I initialized a corpus at "corpus"
    And a file "corpus/extracted/pipeline/bad/manifest.json" exists with contents:
      """
      not json
      """
    When I list extraction snapshots in corpus "corpus"
    Then the extraction snapshot list does not include raw reference "pipeline:bad"

  Scenario: Extraction snapshot list supports filtering by extractor identifier
    Given I initialized a corpus at "corpus"
    And a file "corpus/extracted/.keep" exists with contents:
      """
      keep
      """
    When I list extraction snapshots for extractor "pipeline" in corpus "corpus"
    Then the extraction snapshot list is empty

  Scenario: Extraction snapshot list ignores non-directories and missing manifests
    Given I initialized a corpus at "corpus"
    And a file "corpus/extracted/pipeline/not-a-directory" exists with contents:
      """
      ignore
      """
    And a file "corpus/extracted/pipeline/no-manifest/.keep" exists with contents:
      """
      ignore
      """
    When I list extraction snapshots in corpus "corpus"
    Then the extraction snapshot list does not include raw reference "pipeline:not-a-directory"
    And the extraction snapshot list does not include raw reference "pipeline:no-manifest"

  Scenario: Showing an unknown extraction snapshot fails cleanly
    Given I initialized a corpus at "corpus"
    When I snapshot "extract show --snapshot pipeline:missing" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Missing extraction snapshot manifest"

  Scenario: Deleting an unknown extraction snapshot fails cleanly
    Given I initialized a corpus at "corpus"
    When I snapshot "extract delete --snapshot pipeline:missing --confirm pipeline:missing" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Missing extraction snapshot directory"

  Scenario: Deleting requires exact confirmation
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I remember the last extraction snapshot reference as "first"
    When I attempt to delete extraction snapshot "first" in corpus "corpus" with confirm "nope"
    Then the command fails with exit code 2
    And standard error includes "--confirm"
