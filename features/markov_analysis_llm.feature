@integration @openai
Feature: Markov analysis with provider-backed stages
  Markov analysis can use provider-backed segmentation, observation extraction, and embeddings.

  Scenario: Markov analysis supports LLM segmentation, LLM observations, and embedding-based encoding
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And a fake OpenAI library is available that returns chat completion for prompt containing "SEGMENTER":
      """
      ["Alpha segment", "Beta segment"]
      """
    And a fake OpenAI library is available that returns chat completion for prompt containing "Alpha segment":
      """
      {"label": "greeting", "label_confidence": 0.9, "summary": "Alpha summary"}
      """
    And a fake OpenAI library is available that returns chat completion for prompt containing "Beta segment":
      """
      {"label": "details", "label_confidence": 0.8, "summary": "Beta summary"}
      """
    And a fake OpenAI library is available that returns embedding vector "1.0,0.0" for input text "Alpha summary"
    And a fake OpenAI library is available that returns embedding vector "0.0,1.0" for input text "Beta summary"
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
          prompt_template: "SEGMENTER {text}"
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
          batch_size: 16
          parallelism: 2
        text_source: llm_summary
      observations:
        encoder: embedding
      model:
        family: gaussian
        n_states: 2
      """
    When I snapshot a markov analysis in corpus "corpus" using configuration "markov.yml" and the latest extraction snapshot
    Then the markov analysis output includes 1 decoded item path
    And the markov analysis snapshot includes an observations file
