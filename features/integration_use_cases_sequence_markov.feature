@integration @openai @slow
Feature: Use cases integration (sequence Markov)
  This use case exercises Markov analysis on an ordered-text dataset.

  Scenario: Learn a Markov transition graph from ordered text (real model)
    When I run the use case demo script "sequence_markov_demo.py" with arguments:
      | arg           | value |
      | --ingest-limit | 25    |
      | --config      | text_source.sample_size=25 |
      | --config      | model.n_states=8 |
      | --config      | report.max_state_exemplars=10 |
      | --config      | report.state_naming.max_exemplars_per_state=10 |
    Then the demo transitions dot contains "START"
    And the demo transitions dot contains "END"

