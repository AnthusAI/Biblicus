Feature: Cascading YAML recipes
  Biblicus composes multiple YAML recipe files into a single configuration view, then applies command-line overrides.

  Scenario: Topic analysis composes multiple recipe files and applies --config overrides
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a recipe file "base.yml" exists with content:
      """
      schema_version: 1
      text_source:
        sample_size: 10
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 3
      llm_fine_tuning:
        enabled: false
      """
    And a recipe file "overlay.yml" exists with content:
      """
      bertopic_analysis:
        vectorizer:
          ngram_range: [1, 2]
      """
    And I run a topic analysis in corpus "corpus" using recipes "base.yml,overlay.yml" and the latest extraction run with config overrides:
      | key                               | value |
      | bertopic_analysis.parameters.nr_topics | 7     |
    Then the BERTopic analysis report includes ngram range 1 and 2
    And the topic analysis report includes BERTopic parameter "nr_topics" with value 7

  Scenario: Profiling analysis composes multiple recipe files and applies --config overrides
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I ingest the text "This is a longer document that should remain after filtering. This is a longer document that should remain after filtering. This is a longer document that should remain after filtering. This is a longer document that should remain after filtering." with title "Beta" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a recipe file "base.yml" exists with content:
      """
      schema_version: 1
      sample_size: 500
      min_text_characters: 10
      percentiles: [50, 90]
      """
    And a recipe file "overlay.yml" exists with content:
      """
      min_text_characters: 200
      """
    And I run a profiling analysis in corpus "corpus" using recipes "base.yml,overlay.yml" and the latest extraction run with config overrides:
      | key                 | value |
      | percentiles          | [99]  |
    Then the profiling output includes extracted nonempty items 1
    And the profiling output includes extracted empty items 1
    And the profiling analysis output includes percentile 99
