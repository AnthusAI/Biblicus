Feature: Topic granularity sweep
  Biblicus can compare topic modeling granularity profiles and rerun the selected profile with BERTopic labels.

  Scenario: Granularity sweep selects a profile inside the target range and labels the winning run
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0,1,2,3,4,5,6,7,8,9,10,11" and keywords:
      | topic_id | keywords      |
      | 0        | alpha,topic   |
      | 1        | beta,topic    |
      | 2        | gamma,topic   |
      | 3        | delta,topic   |
      | 4        | epsilon,topic |
      | 5        | zeta,topic    |
      | 6        | eta,topic     |
      | 7        | theta,topic   |
      | 8        | iota,topic    |
      | 9        | kappa,topic   |
      | 10       | lambda,topic  |
      | 11       | mu,topic      |
    And a fake OpenAI library is available that returns chat completion "Labeled Topic" for any prompt
    And an OpenAI API key is configured for this scenario
    When I ingest topic modeling texts into corpus "corpus":
      | title | text         |
      | Doc 0 | alpha body   |
      | Doc 1 | beta body    |
      | Doc 2 | gamma body   |
      | Doc 3 | delta body   |
      | Doc 4 | epsilon body |
      | Doc 5 | zeta body    |
      | Doc 6 | eta body     |
      | Doc 7 | theta body   |
      | Doc 8 | iota body    |
      | Doc 9 | kappa body   |
      | Doc 10 | lambda body |
      | Doc 11 | mu body     |
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "fine.yml" exists with content:
      """
      schema_version: 1
      text_source:
        min_text_characters: 1
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: null
          min_topic_size: 2
        vectorizer:
          ngram_range: [1, 2]
          stop_words: english
        representation_model:
          provider: openai
          model: gpt-5.4-mini
          prompt_template: "Name this topic from [KEYWORDS] and [DOCUMENTS]."
          nr_docs: 3
      """
    And I run a topic granularity sweep in corpus "corpus" using configuration "fine.yml" with target range "10:20" as markdown
    Then the granularity sweep output includes profiles:
      | profile  |
      | coarse   |
      | balanced |
      | fine     |
    And the granularity sweep selected topic count is between 10 and 20
    And the granularity sweep markdown includes "Labeled Topic"
