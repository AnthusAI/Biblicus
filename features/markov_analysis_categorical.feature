@integration @openai
Feature: Markov analysis categorical models
  Markov analysis supports categorical observation sequences.

  Scenario: Markov analysis fits a categorical model using provider-extracted labels
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And a fake OpenAI library is available that returns chat completion for prompt containing "Alpha.":
      """
      {"label": "alpha", "label_confidence": 1.0, "summary": "Alpha"}
      """
    And a fake OpenAI library is available that returns chat completion for prompt containing "Beta.":
      """
      {"label": "beta", "label_confidence": 1.0, "summary": "Beta"}
      """
    And a fake hmmlearn library is available with predicted states "0,1"
    When I ingest the text "Alpha. Beta." with title "Doc" and tags "t" into corpus "corpus"
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
      llm_observations:
        enabled: true
        client:
          provider: openai
          model: gpt-4o-mini
          api_key: test-key
        prompt_template: "{segment}"
      model:
        family: categorical
        n_states: 2
      """
    When I run a markov analysis in corpus "corpus" using recipe "markov.yml" and the latest extraction run
    Then the markov analysis output includes 2 states
    And the markov analysis output includes 1 decoded item path
