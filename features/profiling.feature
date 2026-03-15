Feature: Profiling analysis
  Profiling analysis summarizes raw corpus composition and extracted text coverage.

  Scenario: Profiling analysis reports raw and extracted counts
    Given I initialized a corpus at "corpus"
    And a binary file "blob.bin" exists
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I ingest the file "blob.bin" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I snapshot a profiling analysis in corpus "corpus" using the latest extraction snapshot
    Then the profiling output includes raw item total 2
    And the profiling output includes media type count "text/markdown" 1
    And the profiling output includes media type count "application/octet-stream" 1
    And the profiling output includes raw bytes distribution count 2
    And the profiling output includes raw bytes percentiles 50,90,99
    And the profiling output includes tagged items 1
    And the profiling output includes untagged items 1
    And the profiling output includes top tag "t" with count 1
    And the profiling output includes extracted source items 2
    And the profiling output includes extracted nonempty items 1
    And the profiling output includes extracted empty items 0
    And the profiling output includes extracted missing items 1
    And the profiling output includes extracted text distribution count 1
    And the profiling output includes extracted text percentiles 50,90,99

  Scenario: Profiling analysis uses the latest extraction snapshot when omitted
    Given I initialized a corpus at "corpus"
    And a binary file "blob.bin" exists
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I ingest the file "blob.bin" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I snapshot a profiling analysis in corpus "corpus"
    Then the command succeeds
    And standard error includes "latest extraction snapshot"

  Scenario: Profiling analysis accepts a configuration file
    Given I initialized a corpus at "corpus"
    And a binary file "blob.bin" exists
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I ingest the file "blob.bin" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create a profiling configuration file "profiling_recipe.yml" with:
      """
      schema_version: 1
      sample_size: 1
      percentiles: [50]
      top_tag_count: 1
      """
    And I snapshot a profiling analysis in corpus "corpus" using configuration "profiling_recipe.yml" and the latest extraction snapshot
    Then the profiling output includes raw bytes distribution count 1
    And the profiling output includes raw bytes percentiles 50
    And the profiling output includes top tag "t" with count 1

  Scenario: Profiling analysis reports empty corpus distributions
    Given I initialized a corpus at "corpus"
    When I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I snapshot a profiling analysis in corpus "corpus" using the latest extraction snapshot
    Then the profiling output includes raw item total 0
    And the profiling output includes raw bytes distribution count 0
    And the profiling output includes extracted source items 0
    And the profiling output includes extracted text distribution count 0

  Scenario: Profiling analysis counts empty extracted text
    Given I initialized a corpus at "corpus"
    When I ingest the text "   " with title "Blank" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I snapshot a profiling analysis in corpus "corpus" using the latest extraction snapshot
    Then the profiling output includes extracted nonempty items 0
    And the profiling output includes extracted empty items 1

  Scenario: Profiling analysis respects minimum text length
    Given I initialized a corpus at "corpus"
    When I ingest the text "short" with title "Short" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create a profiling configuration file "profiling_min_text.yml" with:
      """
      schema_version: 1
      min_text_characters: 10
      """
    And I snapshot a profiling analysis in corpus "corpus" using configuration "profiling_min_text.yml" and the latest extraction snapshot
    Then the profiling output includes extracted nonempty items 0
    And the profiling output includes extracted empty items 1

  Scenario: Profiling analysis applies tag filters
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I ingest the text "Beta note" with title "Beta" and tags "other" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create a profiling configuration file "profiling_tags.yml" with:
      """
      schema_version: 1
      tag_filters: ["t"]
      """
    And I snapshot a profiling analysis in corpus "corpus" using configuration "profiling_tags.yml" and the latest extraction snapshot
    Then the profiling output includes top tag "t" with count 1
    And the profiling output includes tagged items 1
    And the profiling output includes untagged items 1

  Scenario: Profiling analysis rejects missing configuration file
    Given I initialized a corpus at "corpus"
    When I snapshot a profiling analysis in corpus "corpus" using configuration "missing.yml" without extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Configuration file not found"

  Scenario: Profiling analysis rejects non-mapping configuration
    Given I initialized a corpus at "corpus"
    When I create a profiling configuration file "profiling_invalid.yml" with:
      """
      - not
      - a
      - mapping
      """
    And I snapshot a profiling analysis in corpus "corpus" using configuration "profiling_invalid.yml" without extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Profiling configuration must be a mapping/object"

  Scenario: Profiling analysis rejects invalid configuration values
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create a profiling configuration file "profiling_invalid_values.yml" with:
      """
      schema_version: 1
      percentiles: ["bad"]
      """
    And I snapshot a profiling analysis in corpus "corpus" using configuration "profiling_invalid_values.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Invalid profiling configuration"

  Scenario: Profiling analysis requires extraction snapshot
    Given I initialized a corpus at "corpus"
    When I snapshot a profiling analysis in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Profiling analysis requires an extraction snapshot"
