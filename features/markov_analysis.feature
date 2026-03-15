Feature: Markov analysis
  Markov analysis learns a directed, weighted state transition graph from sequences of text segments.

  Scenario: Markov analysis returns states, transitions, and per-item decoded paths
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0,1,1"
    When I ingest the text "Alpha. Beta. Gamma." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      text_source:
        sample_size: 10
        min_text_characters: 1
      segmentation:
        method: sentence
      observations:
        encoder: tfidf
        tfidf:
          max_features: 20
          ngram_range: [1, 1]
      model:
        family: gaussian
        n_states: 2
      artifacts:
        graphviz:
          enabled: true
      """
    And I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis output includes 2 states
    And the markov analysis output includes a transition from state 0 to state 1
    And the markov analysis output includes 1 decoded item path
    And the analysis snapshot includes a graphviz transitions file

  Scenario: Markov analysis builds the default extraction snapshot when missing
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Alpha." with title "Doc" and tags "t" into corpus "corpus"
    And I create the directory "corpus/recipes/extraction"
    And a configuration file "corpus/recipes/extraction/default.yml" exists with content:
      """
      extractor_id: pipeline
      configuration:
        stages:
          - extractor_id: pass-through-text
            config: {}
      """
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: sentence
      observations:
        encoder: tfidf
      model:
        family: gaussian
        n_states: 1
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml"
    Then the markov analysis output includes 1 states
    And the markov analysis output references an extraction snapshot with artifacts

  Scenario: Markov analysis reuses the default extraction snapshot built from a recipe using config alias
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Alpha." with title "Doc" and tags "t" into corpus "corpus"
    And I create the directory "corpus/recipes/extraction"
    And a configuration file "corpus/recipes/extraction/default.yml" exists with content:
      """
      extractor_id: pipeline
      configuration:
        stages:
          - extractor_id: pass-through-text
            config: {}
      """
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: sentence
      observations:
        encoder: tfidf
      model:
        family: gaussian
        n_states: 1
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml"
    And I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml"
    Then standard error includes "[extract] reusing snapshot"
