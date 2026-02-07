Feature: Profiling config overrides
  Profiling analysis accepts --config overrides even when no configuration file is provided.

  Scenario: Profiling analysis applies --config overrides without a configuration file
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I ingest the text "This is a longer document that should remain after filtering. This is a longer document that should remain after filtering. This is a longer document that should remain after filtering. This is a longer document that should remain after filtering." with title "Beta" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    When I snapshot a profiling analysis in corpus "corpus" using the latest extraction snapshot with config overrides:
      | key                | value |
      | min_text_characters | 200   |
    Then the profiling output includes extracted nonempty items 1
    And the profiling output includes extracted empty items 1

