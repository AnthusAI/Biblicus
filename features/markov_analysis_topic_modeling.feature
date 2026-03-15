Feature: Markov analysis topic modeling
  Markov analysis can use topic modeling to supply categorical labels for observations.

  Scenario: Topic modeling populates topic labels for Markov observations
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0,1" and keywords:
      | topic_id | keywords         |
      | 0        | billing,invoice  |
      | 1        | refund,credit    |
    And a fake hmmlearn library is available with predicted states "0,1,0,1"
    When I ingest the text "Billing question. Refund request." with title "Doc" and tags "t" into corpus "corpus"
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
      topic_modeling:
        enabled: true
        configuration:
          schema_version: 1
          llm_extraction:
            enabled: false
          lexical_processing:
            enabled: false
          bertopic_analysis:
            parameters: {}
      observations:
        categorical_source: topic_label
      model:
        family: categorical
        n_states: 2
      """
    And I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov observations include topic labels "billing,refund"
