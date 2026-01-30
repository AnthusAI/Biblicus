Feature: Retrieval quality upgrades
  Retrieval quality upgrades keep multi-stage retrieval explicit while improving relevance.

  Scenario: Lexical tuning parameters are recorded in the retrieval recipe
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha bravo charlie"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key                | value |
      | chunk_size         | 200   |
      | chunk_overlap      | 50    |
      | snippet_characters | 120   |
      | bm25_k1            | 1.2   |
      | bm25_b             | 0.75  |
      | ngram_min          | 1     |
      | ngram_max          | 2     |
      | stop_words         | english |
      | field_weight_title | 2.0   |
      | field_weight_body  | 1.0   |
      | field_weight_tags  | 0.5   |
    Then the latest run recipe config includes:
      | key                | value |
      | bm25_k1            | 1.2   |
      | bm25_b             | 0.75  |
      | ngram_min          | 1     |
      | ngram_max          | 2     |
      | stop_words         | english |
      | field_weight_title | 2.0   |
      | field_weight_body  | 1.0   |
      | field_weight_tags  | 0.5   |

  Scenario: Lexical tuning rejects invalid ngram ranges
    Given I initialized a corpus at "corpus"
    When I attempt to build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key       | value |
      | ngram_min | 2     |
      | ngram_max | 1     |
    Then the command fails with exit code 2
    And standard error includes "ngram range"

  Scenario: Stop words exclude common tokens from lexical retrieval
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "the zebra"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key        | value |
      | stop_words | english |
    And I query with the latest run for "the" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query evidence count is 0

  Scenario: Reranking produces explicit stage metadata
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha bravo charlie"
    And a text file "beta.md" exists with contents "alpha beta charlie"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I ingest the file "beta.md" into corpus "corpus"
    And I build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key                 | value |
      | rerank_enabled      | true  |
      | rerank_model        | cross-encoder |
      | rerank_top_k        | 2     |
    And I query with the latest run for "alpha" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query returns evidence with stage "rerank"
    And the query evidence includes stage score "retrieve"
    And the query evidence includes stage score "rerank"
    And the query stats include reranked_candidates 2

  Scenario: Hybrid retrieval records lexical and embedding scores
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha bravo charlie"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "hybrid" retrieval run in corpus "corpus" with config:
      | key              | value |
      | lexical_backend  | sqlite-full-text-search |
      | embedding_backend| vector |
      | lexical_weight   | 0.7   |
      | embedding_weight | 0.3   |
    And I query with the latest run for "alpha" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query returns evidence with stage "hybrid"
    And the query evidence includes stage score "lexical"
    And the query evidence includes stage score "embedding"
    And the query stats include fusion_weights "lexical=0.7,embedding=0.3"

  Scenario: Hybrid retrieval rejects invalid weights
    Given I initialized a corpus at "corpus"
    When I attempt to build a "hybrid" retrieval run in corpus "corpus" with config:
      | key              | value |
      | lexical_weight   | 0.9   |
      | embedding_weight | 0.9   |
    Then the command fails with exit code 2
    And standard error includes "weights must sum to 1"

  Scenario: SQLite stop words reject invalid strings
    Given I initialized a corpus at "corpus"
    When I attempt to build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key        | value   |
      | stop_words | spanish |
    Then the command fails with exit code 2
    And standard error includes "stop_words"

  Scenario: SQLite stop words accept explicit lists
    When I validate sqlite full-text search stop words list:
      | value |
      | the   |
      | and   |
    Then the sqlite stop words include "the"

  Scenario: SQLite stop words reject empty lists
    When I attempt to validate sqlite full-text search stop words list:
      | value |
    Then a model validation error is raised
    And the validation error mentions "stop_words list must not be empty"

  Scenario: SQLite stop words reject empty entries
    When I attempt to validate sqlite full-text search stop words list:
      | value |
      |       |
    Then a model validation error is raised
    And the validation error mentions "stop_words list must contain non-empty strings"

  Scenario: Rerank requires a model identifier
    Given I initialized a corpus at "corpus"
    When I attempt to build a "sqlite-full-text-search" retrieval run in corpus "corpus" with config:
      | key            | value |
      | rerank_enabled | true  |
    Then the command fails with exit code 2
    And standard error includes "rerank_model"

  Scenario: Vector retrieval returns evidence
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha bravo"
    And a text file "plain.txt" exists with contents "alpha plain"
    And a text file "delta.md" exists with contents "delta"
    And a text file "punct.md" exists with contents "!!!"
    And a binary file "data.bin" exists
    When I ingest the file "alpha.md" into corpus "corpus"
    And I ingest the file "plain.txt" into corpus "corpus"
    And I ingest the file "delta.md" into corpus "corpus"
    And I ingest the file "punct.md" into corpus "corpus"
    And I ingest the file "data.bin" into corpus "corpus"
    And I build a "vector" retrieval run in corpus "corpus"
    And I query with the latest run for "alpha" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query returns evidence with stage "vector"

  Scenario: Vector retrieval handles longer queries
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "vector" retrieval run in corpus "corpus"
    And I query with the latest run for "alpha bravo charlie" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query returns evidence with stage "vector"

  Scenario: Vector retrieval ignores empty queries
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "vector" retrieval run in corpus "corpus"
    And I query with the latest run for "!!!" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the query evidence count is 0

  Scenario: Vector retrieval uses extracted text
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha bravo"
    And a text file "whitespace.txt" exists with contents "   "
    And a binary file "data.bin" exists
    When I ingest the file "alpha.md" into corpus "corpus"
    And I ingest the file "whitespace.txt" into corpus "corpus"
    And I ingest the file "data.bin" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "vector" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                | value |
      | snippet_characters | 120   |
    And I query with the latest run for "alpha" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | max_total_characters | 2000  |
      | max_items_per_source | 5     |
    Then the latest run stats include text_items 2

  Scenario: Vector retrieval rejects missing extraction runs
    Given I initialized a corpus at "corpus"
    When I attempt to build a "vector" retrieval run in corpus "corpus" with extraction run "missing:run"
    Then the command fails with exit code 2
    And standard error includes "Missing extraction run"

  Scenario: Vector snippet helpers handle missing spans
    When I compute a vector match span for text "alpha" with tokens "beta"
    Then the vector match span is None
    And the vector snippet for text "alpha" with span "None" and max chars 5 equals "alpha"

  Scenario: Vector match spans ignore empty tokens
    When I compute a vector match span for text "alpha" with tokens "alpha,,beta"
    Then the vector match span is "0..5"

  Scenario: Vector match spans prefer earlier tokens
    When I compute a vector match span for text "alpha beta" with tokens "beta,alpha"
    Then the vector match span is "0..5"

  Scenario: Vector match spans ignore later tokens
    When I compute a vector match span for text "alpha beta" with tokens "alpha,beta"
    Then the vector match span is "0..5"

  Scenario: Vector snippet helpers handle empty text
    When I compute a vector match span for text "<empty>" with tokens "alpha"
    Then the vector match span is None
    And the vector snippet for text "<empty>" with span "None" and max chars 5 equals "<empty>"

  Scenario: Hybrid backend rejects nested lexical backends
    Given I initialized a corpus at "corpus"
    When I attempt to build a "hybrid" retrieval run in corpus "corpus" with config:
      | key             | value |
      | lexical_backend | hybrid |
    Then the command fails with exit code 2
    And standard error includes "lexical"

  Scenario: Hybrid backend rejects nested embedding backends
    Given I initialized a corpus at "corpus"
    When I attempt to build a "hybrid" retrieval run in corpus "corpus" with config:
      | key              | value |
      | lexical_backend  | sqlite-full-text-search |
      | embedding_backend| hybrid |
    Then the command fails with exit code 2
    And standard error includes "embedding"

  Scenario: Hybrid query requires component runs
    Given I initialized a corpus at "corpus"
    When I attempt to query a hybrid run without component runs
    Then a model validation error is raised
    And the validation error mentions "Hybrid run missing lexical or embedding run identifiers"
