Feature: Markov analysis variants
  Markov analysis supports multiple segmentation methods, observation encodings, and configuration error handling.

  Scenario: Markov analysis supports fixed window segmentation
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0,1"
    When I ingest the text "AlphaBetaGammaDeltaEpsilon" with title "Doc" and tags "t" into corpus "corpus"
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
        method: fixed_window
        fixed_window:
          max_characters: 5
          overlap_characters: 0
      observations:
        encoder: tfidf
        tfidf:
          max_features: 20
          ngram_range: [1, 1]
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis snapshot includes more than 1 segment

  Scenario: Markov analysis supports span markup segmentation
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Alpha","new_str":"<span>Alpha</span>"},{"command":"str_replace","old_str":"Beta","new_str":"<span>Beta</span>"}],"done":true}
      """
    And a fake hmmlearn library is available with predicted states "0,1"
    When I ingest the text "Alpha Beta" with title "Doc" and tags "t" into corpus "corpus"
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
        method: span_markup
        span_markup:
          client:
            provider: openai
            model: gpt-4o-mini
            api_key: test-key
          prompt_template: "Return the segments."
          system_prompt: "Current text:\n---\n{text}\n---\n"
      observations:
        encoder: tfidf
        tfidf:
          max_features: 20
          ngram_range: [1, 1]
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis snapshot includes more than 1 segment

  Scenario: Markov analysis supports span markup segmentation with labels
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Greeting","new_str":"<span label=\"greeting\">Greeting</span>"},{"command":"str_replace","old_str":"Wrapup","new_str":"<span label=\"wrapup\">Wrapup</span>"}],"done":true}
      """
    And a fake hmmlearn library is available with predicted states "0,1"
    When I ingest the text "Greeting Wrapup" with title "Doc" and tags "t" into corpus "corpus"
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
        method: span_markup
        span_markup:
          client:
            provider: openai
            model: gpt-4o-mini
            api_key: test-key
          prompt_template: "Return the named segments."
          system_prompt: "Current text:\n---\n{text}\n---\n"
          label_attribute: label
          prepend_label: true
      observations:
        encoder: tfidf
        tfidf:
          max_features: 20
          ngram_range: [1, 1]
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis snapshot includes a segment with text:
      """
      greeting
      Greeting
      """

  Scenario: Markov analysis supports JSON object segmentation output
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns chat completion for prompt containing "SEGMENTER":
      """
      {"segments": ["Alpha segment", "Beta segment"]}
      """
    And a fake hmmlearn library is available with predicted states "0,1"
    When I ingest the text "AlphaBeta" with title "Doc" and tags "t" into corpus "corpus"
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
        method: llm
        llm:
          client:
            provider: openai
            model: gpt-4o-mini
            api_key: test-key
            response_format: json_object
          prompt_template: "SEGMENTER {text}"
      observations:
        encoder: tfidf
        tfidf:
          max_features: 20
          ngram_range: [1, 1]
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis snapshot includes more than 1 segment

  Scenario: Markov analysis computes transitions from decoded sequence when the model does not provide transmat_
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available without transmat_ output
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
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis output includes a transition from state 0 to state 1

  Scenario: Markov analysis fails fast when hmmlearn is not installed
    Given I initialized a corpus at "corpus"
    And the hmmlearn dependency is unavailable
    When I ingest the text "Alpha. Beta." with title "Doc" and tags "t" into corpus "corpus"
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
      """
    When I attempt to snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "biblicus[markov-analysis]"

  Scenario: Markov analysis requires an extraction snapshot when none is available
    Given I initialized a corpus at "corpus"
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml"
    Then the command fails with exit code 2
    And standard error includes "Markov analysis requires an extraction snapshot"

  Scenario: Markov analysis emits a reproducibility warning when using the latest extraction snapshot
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Alpha." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml"
    Then standard error includes "Warning: using latest extraction snapshot"

  Scenario: Markov analysis rejects invalid configurations
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Alpha." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: llm
      """
    When I attempt to snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Invalid Markov analysis configuration"

  Scenario: Markov analysis text collection filters non-extracted, empty, and short documents and truncates by sample size
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Alpha." with title "Doc1" and tags "t" into corpus "corpus"
    And I ingest the text "Beta." with title "Doc2" and tags "t" into corpus "corpus"
    And I ingest the text "Hi" with title "Doc3" and tags "t" into corpus "corpus"
    And I ingest the text "Delta." with title "Doc4" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I append a non-extracted item to the latest extraction snapshot manifest
    And I blank the extracted text for the 4th ingested item in the latest extraction snapshot
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      text_source:
        sample_size: 1
        min_text_characters: 3
      segmentation:
        method: sentence
      observations:
        encoder: tfidf
        tfidf:
          max_features: 10
          ngram_range: [1, 1]
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis text collection report includes:
      | field        | value |
      | source_items | 5     |
      | documents    | 1     |
      | empty_texts  | 1     |
      | skipped_items| 2     |
    And the markov analysis text collection report warnings include "sample_size"

  Scenario: Markov analysis fails when no extracted text documents remain after filtering
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Hi" with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      text_source:
        min_text_characters: 1000
      model:
        family: gaussian
        n_states: 2
      """
    When I attempt to snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "at least one extracted text document"

  Scenario: Markov analysis supports per-item decoded paths and report exemplar caps
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0,1,0,1"
    When I ingest the text "Alpha. Beta." with title "Doc1" and tags "t" into corpus "corpus"
    And I ingest the text "Gamma. Delta." with title "Doc2" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: sentence
      model:
        family: gaussian
        n_states: 2
      report:
        max_state_exemplars: 0
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis output includes 2 decoded item path
    And every Markov state report has no non-boundary exemplars

  Scenario: Markov analysis supports embedding-encoded Gaussian observations
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And a fake hmmlearn library is available with predicted states "0,1"
    When I ingest the text "Alpha. Beta." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: sentence
      embeddings:
        enabled: true
        client:
          provider: openai
          model: text-embedding-3-small
          api_key: test-key
        text_source: segment_text
      observations:
        encoder: embedding
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis snapshot includes an observations file

  Scenario: Markov analysis fails when embedding observations are requested without enabling embeddings
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Alpha." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: sentence
      observations:
        encoder: embedding
      model:
        family: gaussian
        n_states: 2
      """
    When I attempt to snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Embedding observations require embeddings.enabled true"

  Scenario: Markov analysis fails when embeddings require llm summaries but summaries are missing
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Alpha." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: sentence
      embeddings:
        enabled: true
        client:
          provider: openai
          model: text-embedding-3-small
          api_key: test-key
        text_source: llm_summary
      model:
        family: gaussian
        n_states: 2
      """
    When I attempt to snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "llm_summary is missing"

  Scenario: Markov analysis fails when categorical models lack categorical labels
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0"
    When I ingest the text "Alpha." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: sentence
      model:
        family: categorical
        n_states: 2
      """
    When I attempt to snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Categorical Markov models require categorical labels"

  Scenario: Markov analysis supports tfidf encoding from llm summaries, including missing summaries
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And a fake OpenAI library is available that returns chat completion for prompt containing "START":
      """
      {"label": "start", "label_confidence": 1.0, "summary": "Start summary"}
      """
    And a fake OpenAI library is available that returns chat completion for prompt containing "END":
      """
      {"label": "end", "label_confidence": 1.0, "summary": "End summary"}
      """
    And a fake OpenAI library is available that returns chat completion for prompt containing "Alpha.":
      """
      {"label": "alpha", "label_confidence": 1.0, "summary": "Alpha summary"}
      """
    And a fake OpenAI library is available that returns chat completion for prompt containing "Beta.":
      """
      {"label": "beta", "label_confidence": 1.0}
      """
    And a fake hmmlearn library is available with predicted states "0,1"
    When I ingest the text "Alpha. Beta." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: sentence
      llm_observations:
        enabled: true
        client:
          provider: openai
          model: gpt-4o-mini
          api_key: test-key
        prompt_template: "{segment}"
      observations:
        encoder: tfidf
        text_source: llm_summary
        tfidf:
          max_features: 5
          ngram_range: [1, 1]
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis output includes 1 decoded item path

  Scenario: Markov analysis supports hybrid observations combining embeddings and provider labels
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And a fake OpenAI library is available that returns chat completion for prompt containing "START":
      """
      {"label": "start", "label_confidence": 1.0, "summary": "Start summary"}
      """
    And a fake OpenAI library is available that returns chat completion for prompt containing "END":
      """
      {"label": "end", "label_confidence": 1.0, "summary": "End summary"}
      """
    And a fake OpenAI library is available that returns chat completion for prompt containing "Alpha.":
      """
      {"label": "alpha", "label_confidence": 0.9, "summary": "Alpha summary"}
      """
    And a fake OpenAI library is available that returns chat completion for prompt containing "Beta.":
      """
      {"label": "beta", "label_confidence": 0.8, "summary": "Beta summary"}
      """
    And a fake hmmlearn library is available with predicted states "0,1"
    When I ingest the text "Alpha. Beta." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: sentence
      llm_observations:
        enabled: true
        client:
          provider: openai
          model: gpt-4o-mini
          api_key: test-key
        prompt_template: "{segment}"
      embeddings:
        enabled: true
        client:
          provider: openai
          model: text-embedding-3-small
          api_key: test-key
        text_source: segment_text
      observations:
        encoder: hybrid
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis output includes 1 decoded item path

  Scenario: Markov analysis exports GraphViz transitions respecting a minimum edge weight
    Given I initialized a corpus at "corpus"
    And a fake hmmlearn library is available with predicted states "0,1,1"
    When I ingest the text "Alpha. Beta. Gamma." with title "Doc" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And a configuration file "markov.yml" exists with content:
      """
      schema_version: 1
      segmentation:
        method: sentence
      model:
        family: gaussian
        n_states: 2
      artifacts:
        graphviz:
          enabled: true
          min_edge_weight: 2.0
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the graphviz transitions file contains no edges
