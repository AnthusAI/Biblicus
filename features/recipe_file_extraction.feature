Feature: Extraction snapshot configuration files
  Extraction runs can be built from YAML configuration files instead of inline CLI arguments.

  Scenario: Build extraction snapshot from configuration file with nested config
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha" with title "Alpha" and tags "a" into corpus "corpus"
    And a configuration file "configuration.yml" exists with content:
      """
      extractor_id: pass-through-text
      configuration: {}
      """
    And I build an extraction snapshot in corpus "corpus" using configuration file "configuration.yml"
    Then the extraction snapshot includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "alpha"

  Scenario: Build extraction snapshot from configuration file with pipeline extractor
    Given I initialized a corpus at "corpus"
    When I ingest the text "beta" with title "Beta" and tags "b" into corpus "corpus"
    And a configuration file "pipeline-configuration.yml" exists with content:
      """
      extractor_id: pipeline
      configuration:
        stages:
          - extractor_id: pass-through-text
            configuration: {}
      """
    And I build an extraction snapshot in corpus "corpus" using configuration file "pipeline-configuration.yml"
    Then the extraction snapshot includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "beta"

  Scenario: Configuration file not found
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction snapshot in corpus "corpus" using configuration file "missing.yml"
    Then the command fails with exit code 2
    And standard error includes "Configuration file not found"
