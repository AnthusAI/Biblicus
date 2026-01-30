Feature: Analysis schema validation
  Analysis schemas are strict and raise explicit errors on invalid inputs.

  Scenario: Unknown analysis backend is rejected
    When I attempt to resolve analysis backend "unknown-backend"
    Then the analysis backend error mentions "Unknown analysis backend"

  Scenario: Analysis backend base class is not implemented
    When I invoke the analysis backend base class
    Then a not implemented error is raised

  Scenario: LLM client config accepts enum provider
    When I validate an LLM client config with enum provider
    Then the LLM client config provider equals "openai"

  Scenario: LLM client config rejects invalid provider type
    When I attempt to validate an LLM client config with invalid provider type
    Then a model validation error is raised
    And the validation error mentions "llm client provider must be a string or LlmProvider"

  Scenario: LLM extraction config accepts enum method
    When I validate an LLM extraction config with enum method
    Then the LLM extraction config method equals "single"

  Scenario: LLM extraction config rejects invalid method type
    When I attempt to validate an LLM extraction config with invalid method type
    Then a model validation error is raised
    And the validation error mentions "llm_extraction.method must be a string or TopicModelingLlmExtractionMethod"

  Scenario: LLM fine-tuning handles missing document references
    When I run LLM fine-tuning with missing document references
    Then the fine-tuning topics labeled equals 1

  Scenario: Itemized response parses JSON string
    When I parse an itemized response JSON string
    Then the itemized response contains 2 items

  Scenario: Vectorizer stop words accepts list
    When I validate a vectorizer config with stop words list
    Then the vectorizer stop words includes "the"

  Scenario: Vectorizer stop words accepts english
    When I validate a vectorizer config with stop words english
    Then the vectorizer stop words equals "english"

  Scenario: Vectorizer stop words rejects invalid entries
    When I attempt to validate a vectorizer config with invalid stop words
    Then a model validation error is raised
    And the validation error mentions "vectorizer.stop_words must be"

  Scenario: Vectorizer stop words allows None
    When I validate a vectorizer config with no stop words
    Then the vectorizer stop words are absent

  Scenario: Vectorizer stop words rejects invalid string
    When I attempt to validate a vectorizer config with stop words "spanish"
    Then a model validation error is raised
    And the validation error mentions "vectorizer.stop_words must be"

  Scenario: Profiling config rejects invalid sample size
    When I attempt to validate a profiling config with sample size 0
    Then a model validation error is raised
    And the validation error mentions "sample_size"

  Scenario: Profiling config rejects unsupported schema version
    When I attempt to validate a profiling config with schema version 2
    Then a model validation error is raised
    And the validation error mentions "Unsupported analysis schema version"

  Scenario: Profiling config rejects invalid percentiles
    When I attempt to validate a profiling config with percentiles "0,101"
    Then a model validation error is raised
    And the validation error mentions "percentiles"

  Scenario: Profiling config rejects empty percentiles
    When I attempt to validate a profiling config with empty percentiles
    Then a model validation error is raised
    And the validation error mentions "percentiles"

  Scenario: Profiling config rejects unsorted percentiles
    When I attempt to validate a profiling config with percentiles "90,50"
    Then a model validation error is raised
    And the validation error mentions "percentiles"

  Scenario: Profiling config rejects empty tag filters
    When I attempt to validate a profiling config with tag filters "alpha,,beta"
    Then a model validation error is raised
    And the validation error mentions "tag_filters"

  Scenario: Profiling config rejects non-list tag filters
    When I attempt to validate a profiling config with tag filters string "alpha"
    Then a model validation error is raised
    And the validation error mentions "tag_filters"

  Scenario: Profiling config accepts tag filters None
    When I validate a profiling config with tag filters None
    Then the profiling tag filters are absent

  Scenario: Profiling config normalizes tag filters
    When I validate a profiling config with tag filters list " alpha ,beta "
    Then the profiling tag filters include "alpha"
    And the profiling tag filters include "beta"

  Scenario: Profiling ordering helper ignores missing items
    When I order catalog items with missing entries
    Then the ordered catalog item identifiers equal "a,c,b"

  Scenario: Profiling percentile helper handles empty values
    When I compute a profiling percentile on empty values
    Then the profiling percentile value equals 0
