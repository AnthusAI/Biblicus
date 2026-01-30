Feature: Extraction run recipe files
  Extraction runs can be built from YAML recipe files instead of inline CLI arguments.

  Scenario: Build extraction run from recipe file with nested config
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha" with title "Alpha" and tags "a" into corpus "corpus"
    And a recipe file "recipe.yml" exists with content:
      """
      extractor_id: pass-through-text
      config: {}
      """
    And I build an extraction run in corpus "corpus" using recipe file "recipe.yml"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "alpha"

  Scenario: Build extraction run from recipe file with pipeline extractor
    Given I initialized a corpus at "corpus"
    When I ingest the text "beta" with title "Beta" and tags "b" into corpus "corpus"
    And a recipe file "pipeline-recipe.yml" exists with content:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: pass-through-text
            config: {}
      """
    And I build an extraction run in corpus "corpus" using recipe file "pipeline-recipe.yml"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "beta"

  Scenario: Recipe file not found
    Given I initialized a corpus at "corpus"
    When I attempt to build an extraction run in corpus "corpus" using recipe file "missing.yml"
    Then the command fails with exit code 2
    And standard error includes "Recipe file not found"
