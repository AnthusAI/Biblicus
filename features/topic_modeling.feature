Feature: Topic modeling analysis
  Topic modeling analyzes extracted text and returns structured JSON output.

  Scenario: Topic analysis returns BERTopic topics
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0,1" and keywords:
      | topic_id | keywords    |
      | 0        | alpha,beta  |
      | 1        | gamma,delta |
    And a binary file "blob.bin" exists
    And a text file "empty.txt" exists with contents " "
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I ingest the text "Gamma note" with title "Gamma" and tags "t" into corpus "corpus"
    And I ingest the file "blob.bin" into corpus "corpus"
    And I ingest the file "empty.txt" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: true
        lowercase: true
        strip_punctuation: true
        collapse_whitespace: true
      bertopic_analysis:
        parameters:
          nr_topics: 2
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the topic analysis output includes 2 topics
    And the topic analysis output includes topic labels:
      | label |
      | alpha |
      | gamma |

  Scenario: Topic analysis removes entities before BERTopic
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake spaCy library is available with entities:
      | text  | label  |
      | Alice | PERSON |
    When I ingest the text "Alice requested the address." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      entity_removal:
        enabled: true
        provider: spacy
        model: en_core_web_sm
        entity_types: [PERSON]
        replace_with: ""
        collapse_whitespace: true
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the BERTopic input documents do not include "Alice"

  Scenario: Topic analysis reuses cached entity removal when spaCy is unavailable
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake spaCy library is available with entities:
      | text  | label  |
      | Alice | PERSON |
    When I ingest the text "Alice requested the address." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      entity_removal:
        enabled: true
        provider: spacy
        model: en_core_web_sm
        entity_types: [PERSON]
        replace_with: ""
        collapse_whitespace: true
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    And the spaCy dependency is unavailable
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command succeeds
    And the analysis manifest includes artifact path "entity_removal.jsonl"

  Scenario: Topic analysis reports vectorizer ngram range
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
        vectorizer:
          ngram_range: [1, 2]
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the BERTopic analysis report includes ngram range 1 and 2

  Scenario: Topic analysis reports stop words
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
        vectorizer:
          ngram_range: [1, 2]
          stop_words: english
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the BERTopic analysis report includes stop words "english"

  Scenario: Topic analysis passes an OpenAI representation model into BERTopic
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords       |
      | 0        | alpha,beta     |
    And a fake OpenAI library is available that returns chat completion "Specific Label" for any prompt
    And an OpenAI API key is configured for this scenario
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
        representation_model:
          provider: openai
          model: gpt-5.4-mini
          prompt_template: "Name this topic from [KEYWORDS] and [DOCUMENTS]."
          nr_docs: 3
          delay_in_seconds: 0
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the BERTopic constructor received a representation model
    And the OpenAI client was configured with API key "test-openai-key"
    And the BERTopic representation model used OpenAI model "gpt-5.4-mini"
    And the topic analysis output includes topic label "Specific Label"
    And the topic analysis output label source is "llm"
    And the OpenAI chat request omitted parameter "stop"

  Scenario: Topic analysis rejects OpenAI representation model without the OpenAI dependency
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And the OpenAI dependency is unavailable
    And an OpenAI API key is configured for this scenario
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
        representation_model:
          provider: openai
          model: gpt-5.4-mini
          prompt_template: "Name this topic from [KEYWORDS] and [DOCUMENTS]."
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "OpenAI representation model requires the openai package"

  Scenario: Topic analysis rejects OpenAI representation model without an API key
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available
    And no OpenAI API key is configured
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
        representation_model:
          provider: openai
          model: gpt-5.4-mini
          prompt_template: "Name this topic from [KEYWORDS] and [DOCUMENTS]."
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "OpenAI API key"

  Scenario: Topic analysis uses vectorizer model when available
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library without a fake marker is available
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
        vectorizer:
          ngram_range: [1, 2]
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the BERTopic analysis report includes ngram range 1 and 2

  Scenario: Topic analysis rejects vectorizer without scikit-learn
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library without a fake marker is available
    And the scikit-learn dependency is unavailable
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
        vectorizer:
          ngram_range: [1, 2]
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Vectorizer configuration requires scikit-learn"

  Scenario: Topic analysis rejects invalid ngram range
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
        vectorizer:
          ngram_range: [0, 2]
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "vectorizer.ngram_range must include two integers"

  Scenario: Topic analysis rejects invalid stop words
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
        vectorizer:
          ngram_range: [1, 2]
          stop_words: 7
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "vectorizer.stop_words must be"

  Scenario: Topic analysis truncates sample size
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I ingest the text "Beta note" with title "Beta" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source:
        sample_size: 1
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the topic analysis output includes 1 topics

  Scenario: Topic analysis rejects non-integer sample size
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source:
        sample_size: "two"
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Invalid topic modeling configuration"

  Scenario: Topic analysis fails without extracted text
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a binary file "blob.bin" exists
    When I ingest the file "blob.bin" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "at least one extracted text document"

  Scenario: Topic analysis itemizes text with LLM extraction
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0,1" and keywords:
      | topic_id | keywords    |
      | 0        | alpha       |
      | 1        | beta        |
    And a fake OpenAI library is available that returns chat completion "[\"First item\", \"Second item\"]" for any prompt
    And an OpenAI API key is configured for this scenario
    When I ingest the text "One note" with title "One" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: itemize
        client:
          provider: openai
          model: gpt-4o-mini
        system_prompt: "System directive"
        prompt_template: "Return JSON list: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 2
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the topic analysis output llm extraction output documents equals 2

  Scenario: Topic analysis fails when LLM extraction returns empty output
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available that returns chat completion "" for any prompt
    And an OpenAI API key is configured for this scenario
    When I ingest the text "One note" with title "One" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: single
        client:
          provider: openai
          model: gpt-4o-mini
        prompt_template: "Extract: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "LLM extraction produced no usable documents"

  Scenario: Topic analysis fails when LLM itemization returns non-list JSON
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available that returns chat completion "{}" for any prompt
    And an OpenAI API key is configured for this scenario
    When I ingest the text "One note" with title "One" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: itemize
        client:
          provider: openai
          model: gpt-4o-mini
        prompt_template: "Return JSON list: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "LLM extraction produced no usable documents"

  Scenario: Topic analysis warns when using the latest extraction snapshot
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "First note" with title "First" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I ingest the text "Second note" with title "Second" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    When I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml"
    Then standard error includes "latest extraction snapshot"
    And the topic analysis output uses the latest extraction snapshot reference

  Scenario: Topic analysis requires BERTopic
    Given I initialized a corpus at "corpus"
    And the BERTopic dependency is unavailable
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters: {}
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "biblicus[topic-modeling]"

  Scenario: Topic analysis requires OpenAI API key for LLM extraction
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: single
        client:
          provider: openai
          model: gpt-4o-mini
        prompt_template: "Extract: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "OPENAI_API_KEY"

  Scenario: Topic analysis requires DSPy dependency for LLM extraction
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And the DSPy dependency is unavailable
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: single
        client:
          provider: openai
          model: gpt-4o-mini
        prompt_template: "Extract: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "biblicus[dspy]"

  Scenario: Topic analysis rejects missing LLM extraction prompt
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available
    And an OpenAI API key is configured for this scenario
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: single
        client:
          provider: openai
          model: gpt-4o-mini
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "llm_extraction.prompt_template"

  Scenario: Topic analysis rejects invalid LLM extraction prompt
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available
    And an OpenAI API key is configured for this scenario
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: single
        client:
          provider: openai
          model: gpt-4o-mini
        prompt_template: "No placeholder"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "prompt_template"

  Scenario: Topic analysis skips text below minimum characters
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Tiny" with title "Short" and tags "t" into corpus "corpus"
    And I ingest the text "This is a longer note" with title "Long" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source:
        min_text_characters: 10
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the topic analysis output includes 1 topics

  Scenario: Topic analysis applies lexical processing without normalization
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha  Note!" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: true
        lowercase: false
        strip_punctuation: false
        collapse_whitespace: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the topic analysis output includes 1 topics

  Scenario: Topic analysis accepts single LLM extraction output
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available that returns chat completion "Extracted text" for any prompt
    And an OpenAI API key is configured for this scenario
    When I ingest the text "One note" with title "One" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: single
        client:
          provider: openai
          model: gpt-4o-mini
        prompt_template: "Extract: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the topic analysis output llm extraction output documents equals 1

  Scenario: Topic analysis fails when LLM itemization returns empty output
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available that returns chat completion "" for any prompt
    And an OpenAI API key is configured for this scenario
    When I ingest the text "One note" with title "One" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: itemize
        client:
          provider: openai
          model: gpt-4o-mini
        prompt_template: "Return JSON list: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "LLM extraction produced no usable documents"

  Scenario: Topic analysis fails when LLM itemization returns invalid JSON
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available that returns chat completion "not json" for any prompt
    And an OpenAI API key is configured for this scenario
    When I ingest the text "One note" with title "One" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: itemize
        client:
          provider: openai
          model: gpt-4o-mini
        prompt_template: "Return JSON list: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "LLM extraction produced no usable documents"

  Scenario: Topic analysis itemizes list entries with mixed types
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available that returns chat completion "[\"First\", \"\", 123]" for any prompt
    And an OpenAI API key is configured for this scenario
    When I ingest the text "One note" with title "One" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: itemize
        client:
          provider: openai
          model: gpt-4o-mini
        prompt_template: "Return JSON list: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the topic analysis output llm extraction output documents equals 1

  Scenario: Topic analysis rejects missing LLM extraction client
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: single
        prompt_template: "Extract: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "llm_extraction.client"

  Scenario: Topic analysis rejects unsupported schema version
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 999
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Unsupported analysis schema version"

  Scenario: Topic analysis fails when itemized JSON string is invalid
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a fake OpenAI library is available that returns chat completion "\"not json\"" for any prompt
    And an OpenAI API key is configured for this scenario
    When I ingest the text "One note" with title "One" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: true
        method: itemize
        client:
          provider: openai
          model: gpt-4o-mini
        prompt_template: "Return JSON list: {text}"
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "LLM extraction produced no usable documents"

  Scenario: Topic analysis rejects missing configuration file
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I snapshot a topic analysis in corpus "corpus" using configuration "missing.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Configuration file not found"

  Scenario: Topic analysis rejects non-mapping configuration file
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "topic.yml" exists with content:
      """
      - not
      - a
      - mapping
      """
    And I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Topic modeling configuration must be a mapping/object"

  Scenario: Topic analysis rejects missing extraction snapshot reference
    Given I initialized a corpus at "corpus"
    And a fake BERTopic library is available with topic assignments "0" and keywords:
      | topic_id | keywords |
      | 0        | alpha    |
    And a configuration file "topic.yml" exists with content:
      """
      schema_version: 1
      text_source: {}
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    When I snapshot a topic analysis in corpus "corpus" using configuration "topic.yml"
    Then the command fails with exit code 2
    And standard error includes "Topic analysis requires an extraction snapshot to supply text inputs"
