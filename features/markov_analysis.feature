Feature: Markov analysis
  Markov analysis learns a directed, weighted state transition graph from sequences of text segments.

  Scenario: Markov analysis returns states, transitions, and per-item decoded paths
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0,1,1"
    When I ingest the text "Alpha. Beta. Gamma." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a recipe file "markov.yml" exists with content:
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
    And I run a markov analysis in corpus "corpus" using recipe "markov.yml" and the latest extraction run
    Then the markov analysis output includes 2 states
    And the markov analysis output includes a transition from state 0 to state 1
    And the markov analysis output includes 1 decoded item path
    And the analysis run includes a graphviz transitions file

