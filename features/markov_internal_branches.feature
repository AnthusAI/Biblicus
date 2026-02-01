Feature: Markov analysis internal utilities
  Markov analysis utilities are strict and produce explicit errors for invalid inputs.

  Scenario: Fixed window segmentation validates parameters
    When I attempt fixed window segmentation with max_characters 0 and overlap_characters 0
    Then a ValueError is raised
    And the ValueError message includes "max_characters must be positive"
    When I attempt fixed window segmentation with max_characters 5 and overlap_characters -1
    Then a ValueError is raised
    And the ValueError message includes "overlap_characters must be non-negative"
    When I attempt fixed window segmentation with max_characters 5 and overlap_characters 5
    Then a ValueError is raised
    And the ValueError message includes "must be smaller than max_characters"

  Scenario: Fixed window segmentation skips empty chunks and supports overlaps
    When I run fixed window segmentation on text "AAAAA     BBBBB" with max_characters 5 and overlap_characters 0
    Then the fixed window segmentation returns 2 segments
    When I run fixed window segmentation on empty text with max_characters 5 and overlap_characters 0
    Then the fixed window segmentation returns 0 segments
    When I run fixed window segmentation on text "ABCDEFGHIJ" with max_characters 5 and overlap_characters 2
    Then the fixed window segmentation returns more than 1 segment

  Scenario: Markov JSON parsing helpers reject empty outputs, invalid JSON, and wrong types
    When I attempt to parse JSON list "" for label "LLM segmentation"
    Then a ValueError is raised
    And the ValueError message includes "empty output"
    When I attempt to parse JSON list "{ }" for label "LLM segmentation"
    Then a ValueError is raised
    And the ValueError message includes "JSON list"
    When I attempt to parse JSON list "not json" for label "LLM segmentation"
    Then a ValueError is raised
    And the ValueError message includes "invalid JSON"
    When I attempt to parse JSON object "" for label "LLM observations"
    Then a ValueError is raised
    And the ValueError message includes "empty output"
    When I attempt to parse JSON object "[1,2]" for label "LLM observations"
    Then a ValueError is raised
    And the ValueError message includes "JSON object"
    When I attempt to parse JSON object "not json" for label "LLM observations"
    Then a ValueError is raised
    And the ValueError message includes "invalid JSON"

  Scenario: Markov analysis rejects unsupported segmentation and observation encoders at runtime
    When I attempt to segment documents with unsupported segmentation method
    Then a ValueError is raised
    And the ValueError message includes "Unsupported segmentation method"
    When I attempt to encode observations with unsupported observations encoder
    Then a ValueError is raised
    And the ValueError message includes "Unsupported observations encoder"
    When I attempt to encode hybrid observations with missing embeddings
    Then a ValueError is raised
    And the ValueError message includes "Hybrid observations require embeddings.enabled true"
    When I encode hybrid observations using categorical_source "llm_summary" and numeric_source "segment_index"
    Then the hybrid encoding vector width equals 4
    And the hybrid encoding numeric feature equals 2.0
    When I attempt to segment documents that produce no segments
    Then a ValueError is raised
    And the ValueError message includes "produced no segments"

  Scenario: LLM segmentation requires llm configuration and filters empty segments
    When I attempt to segment a document with llm method but missing llm config
    Then a ValueError is raised
    And the ValueError message includes "segmentation.llm is required"
    When I attempt llm segmentation with json object segments not a list
    Then a ValueError is raised
    And the ValueError message includes "segments' list"
    When I run llm segmentation that returns an empty segment and "Alpha"
    Then the llm segmentation returns 1 segment

  Scenario: Span markup segmentation requires config and skips empty spans
    When I attempt span markup segmentation with missing config
    Then a ValueError is raised
    And the ValueError message includes "segmentation.span_markup is required"
    When I run span markup segmentation with an empty span and "Alpha"
    Then the span markup segmentation returns 1 segment

  Scenario: TFIDF encoding validates inputs and ignores out-of-vocabulary terms
    When I attempt to tfidf encode texts with max_features 0 and ngram_range [1, 1]
    Then a ValueError is raised
    And the ValueError message includes "max_features must be positive"
    When I attempt to tfidf encode texts with max_features 5 and ngram_range [2, 1]
    Then a ValueError is raised
    And the ValueError message includes "ngram_range is invalid"
    When I tfidf encode texts with max_features 1 and ngram_range [1, 1]
    Then the tfidf encoding produces vectors with width 1

  Scenario: Markov model fitting works without numpy for both categorical and gaussian observations
    Given a fake hmmlearn library is available with predicted states "0,1"
    When I fit and decode a categorical Markov model without numpy
    Then the fit and decode returns predicted states
    When I fit and decode a gaussian Markov model without numpy
    Then the fit and decode returns predicted states

  Scenario: Markov observations embed llm summaries
    Given a fake OpenAI library is available
    When I build observations with embeddings from llm summaries
    Then the observations include embeddings

  Scenario: Categorical observation encoding uses labels
    When I encode categorical observations
    Then the categorical encoding includes integers

  Scenario: Markov model fitting uses numpy when available
    Given a fake hmmlearn library is available with predicted states "0,1"
    When I fit and decode a categorical Markov model with numpy
    Then the fit and decode returns predicted states
    When I fit and decode a gaussian Markov model with numpy
    Then the fit and decode returns predicted states

  Scenario: Markov model fitting normalizes nonzero start probabilities
    Given a fake hmmlearn library is available with start probabilities "0.2,0.8"
    When I fit and decode a categorical Markov model without numpy
    Then the fit and decode returns predicted states

  Scenario: Markov model fitting handles missing start probabilities and transmat output
    Given a fake hmmlearn library is available without start probabilities
    And a fake hmmlearn library is available without transmat_ output
    When I fit and decode a categorical Markov model without numpy
    Then the fit and decode returns predicted states
    When I fit and decode a gaussian Markov model without numpy
    Then the fit and decode returns predicted states

  Scenario: Markov state naming context pack fits token budget
    When I build a Markov state naming context pack with a token budget of 8
    Then the state naming context pack includes 1 block

  Scenario: Markov state naming assigns labels from provider response
    When I assign Markov state names with a provider response
    Then the Markov state labels include:
      | state_id | label            |
      | 0        | greeting          |
      | 1        | billing question  |

  Scenario: Markov state naming rejects non-noun phrases
    When I assign Markov state names with a verb phrase response
    Then the Markov state naming fails with "short noun phrases"

  Scenario: Markov state naming validation rejects malformed responses
    When I validate state naming response with "empty name"
    Then a ValueError is raised
    And the ValueError message includes "short noun phrases"
    When I validate state naming response with "punctuation"
    Then a ValueError is raised
    And the ValueError message includes "punctuation"
    When I validate state naming response with "infinitive phrase"
    Then a ValueError is raised
    And the ValueError message includes "short noun phrases"
    When I validate state naming response with "duplicate state id"
    Then a ValueError is raised
    And the ValueError message includes "duplicate state_id"
    When I validate state naming response with "duplicate state name"
    Then a ValueError is raised
    And the ValueError message includes "duplicate state names"
    When I validate state naming response with "missing state ids"
    Then a ValueError is raised
    And the ValueError message includes "missing required state_id"

  Scenario: Markov state naming assigns START/END labels and retries
    When I assign Markov state names with retries
    Then the Markov state labels include:
      | state_id | label           |
      | 0        | START           |
      | 1        | END             |
      | 2        | Initial contact |

  Scenario: Markov state naming handles missing client and empty states
    When I attempt to assign Markov state names without a client
    Then a ValueError is raised
    And the ValueError message includes "report.state_naming.client"
    When I assign Markov state names with no states
    Then the Markov state naming returns no states

  Scenario: Markov state naming fails after retries when responses never validate
    When I attempt to assign Markov state names with retries exhausted
    Then a ValueError is raised
    And the ValueError message includes "failed after retries"

  Scenario: Markov state naming keeps states without labels when validation is patched
    When I assign Markov state names with a missing label in validation output
    Then the Markov state labels include:
      | state_id | label |
      | 0        | Alpha |
      | 1        |       |

  Scenario: Span markup segmentation enforces labels and end verification
    When I attempt span markup segmentation with prepend label but no label attribute
    Then a ValueError is raised
    And the ValueError message includes "label_attribute"
    When I attempt span markup segmentation with missing label value
    Then a ValueError is raised
    And the ValueError message includes "missing label attribute"
    When I apply start/end labels with an end verifier decision
    Then the end label is applied to the final segment
    When I verify end label without a verifier configured
    Then the end label verification returns no decision
    When I apply start/end labels with no payloads
    Then the start/end labeling returns 0 segments
    When I attempt to apply start/end labels without span markup config
    Then a ValueError is raised
    And the ValueError message includes "segmentation.span_markup is required"

  Scenario: Markov state naming context pack returns empty when disabled
    When I build a Markov state naming context pack with state naming disabled
    Then the state naming context pack includes 0 block

  Scenario: GraphViz export infers start/end roles and skips end-state edges
    When I write a GraphViz transitions file with inferred start/end states
    Then the graphviz output includes start and end ranks
    And the graphviz output omits end-state edges
    And the graphviz output includes model-only edge labels

  Scenario: GraphViz export honors explicit start/end state ids
    When I write a GraphViz transitions file with explicit start/end states
    Then the graphviz output includes start state 2
    And the graphviz output includes end state 0

  Scenario: Boundary segment insertion returns empty list for empty input
    When I add markov boundary segments for an empty segment list
    Then the markov boundary segments result is empty

  Scenario: Span markup start/end labeling skips empty payloads and prefixes rejected end segments with a reason
    Given the Markov end label verifier returns:
      """
      {"is_end": false, "reason": "truncated"}
      """
    When I apply start/end labels to span-markup payloads for item "item":
      """
      [{"text":"  "},{"text":"Alpha"},{"text":"Omega"}]
      """
    Then the start/end labeled segments include a prefixed START segment
    And the start/end labeled segments include a rejected END segment with a reason

  Scenario: Span markup start/end labeling skips end labeling when the end label is not configured
    When I apply start/end labels without an end label for item "item":
      """
      [{"text":"Alpha"},{"text":"Omega"}]
      """
    Then the end label is not applied to the final segment

  Scenario: Span markup end verifier rejection leaves the final segment unchanged when no reject label is configured
    Given the Markov end label verifier returns:
      """
      {"is_end": false, "reason": "truncated"}
      """
    When I apply start/end labels with rejected end but no rejection label for item "item":
      """
      [{"text":"Alpha"},{"text":"Omega"}]
      """
    Then the end label is not applied to the final segment

  Scenario: Span markup end verifier rejection omits the reason line when no reason is returned
    Given the Markov end label verifier returns:
      """
      {"is_end": false}
      """
    When I apply start/end labels with rejected end and no reason for item "item":
      """
      [{"text":"Alpha"},{"text":"Omega"}]
      """
    Then the rejected END segment includes no reason line

  Scenario: Topic modeling stage rejects missing recipe and missing documents
    When I attempt to apply topic modeling with enabled true but no recipe
    Then a ValueError is raised
    And the ValueError message includes "topic_modeling.recipe is required"
    When I attempt to apply topic modeling with only boundary segments
    Then a ValueError is raised
    And the ValueError message includes "requires at least one non-boundary segment"

  Scenario: Topic modeling stage rejects missing assignments
    When I attempt to apply topic modeling that returns no assignment for a segment
    Then a ValueError is raised
    And the ValueError message includes "did not return an assignment"

  Scenario: Build states skips out-of-range predicted state ids and preserves boundary tokens under max exemplars
    When I build markov states with an out-of-range predicted state id
    Then the built markov states include no exemplars for the unknown state id
    When I build markov states with max exemplars 1 and a boundary token
    Then the built markov state exemplars end with "START"

  Scenario: State naming applies boundary labels when only boundary states exist
    When I assign markov state names with only START and END states
    Then the assigned markov state labels include "START"
    And the assigned markov state labels include "END"

  Scenario: Boundary label helper preserves non-boundary states
    When I apply markov boundary labels with a middle state
    Then the middle markov state label remains "Middle"

  Scenario: Position stats skip single-state paths
    When I compute state position stats with a single-state decoded path
    Then the computed position stats are empty

  Scenario: GraphViz writer filters unobserved transitions and can omit boundary ranks
    When I write a GraphViz file for a model with no boundary exemplars and an unobserved edge
    Then the GraphViz file does not include start and end ranks
    And the GraphViz file does not contain "0 -> 2"
