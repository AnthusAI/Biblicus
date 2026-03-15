Feature: Markov observation cache
  Markov analysis reuses cached LLM observation labels across runs and preserves topic modeling reports.

  Scenario: Markov analysis reuses cached LLM observations when DSPy is unavailable
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns chat completion "{\"label\": \"greeting\", \"label_confidence\": 0.9, \"summary\": \"Greets the caller\"}" for any prompt
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Hello there. Goodbye now." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      text_source:
        sample_size: 2
        min_text_characters: 1
      segmentation:
        method: sentence
      llm_observations:
        enabled: true
        cache:
          enabled: true
          cache_name: unit-test
        client:
          provider: openai
          model: gpt-4o-mini
          api_key: test-key
        prompt_template: "Label: {segment}"
      observations:
        encoder: tfidf
        tfidf:
          max_features: 20
          ngram_range: [1, 1]
      model:
        family: gaussian
        n_states: 1
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Given the DSPy dependency is unavailable
    And a configuration file "markov-sample.yml" exists with content:
      """
      schema_version: 1
      text_source:
        sample_size: 1
        min_text_characters: 1
      segmentation:
        method: sentence
      llm_observations:
        enabled: true
        cache:
          enabled: true
          cache_name: unit-test
        client:
          provider: openai
          model: gpt-4o-mini
          api_key: test-key
        prompt_template: "Label: {segment}"
      observations:
        encoder: tfidf
        tfidf:
          max_features: 20
          ngram_range: [1, 1]
      model:
        family: gaussian
        n_states: 1
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov-sample.yml" and the latest extraction snapshot
    Then the command succeeds

  Scenario: Markov analysis retains topic modeling report when observations are cached
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0,0" and keywords:
      | topic_id | keywords |
      | 0        | greet:1 |
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Hello there. Goodbye now." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      text_source:
        sample_size: 2
        min_text_characters: 1
      segmentation:
        method: sentence
      topic_modeling:
        enabled: true
        configuration:
          schema_version: 1
          bertopic_analysis:
            parameters: {}
      observations:
        encoder: tfidf
        tfidf:
          max_features: 20
          ngram_range: [1, 1]
      model:
        family: gaussian
        n_states: 1
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis output includes a topic modeling report
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis output includes a topic modeling report
