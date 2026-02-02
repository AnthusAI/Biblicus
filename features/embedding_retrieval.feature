Feature: Embedding retrieval and chunking
  Embedding retrieval builds a reusable index over chunks and returns evidence with provenance.

  Scenario: File-backed embedding index builds artifacts and returns evidence
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 200 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "embedding-index-file" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                            | value |
      | snippet_characters             | 200   |
      | chunker.chunker_id             | fixed-char-window |
      | chunker.window_characters      | 800   |
      | chunker.overlap_characters     | 200   |
      | embedding_provider.provider_id | hash-embedding |
      | embedding_provider.dimensions  | 64    |
    And I measure the latest run artifact bytes
    Then the run artifact bytes are greater than 0
    When I query with the latest run for "United States" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | maximum_total_characters | 1000  |
      | max_items_per_source | 5     |
    Then the query returns evidence with stage "embedding-index-file"
    And the query evidence includes span offsets

  Scenario: Embedding retrieval supports pagination via offset
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 200 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "embedding-index-inmemory" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                            | value             |
      | snippet_characters             | 200               |
      | chunker.chunker_id             | fixed-char-window |
      | chunker.window_characters      | 800               |
      | chunker.overlap_characters     | 200               |
      | embedding_provider.provider_id | hash-embedding    |
      | embedding_provider.dimensions  | 32                |
    When I query with the latest run for "United States" and budget:
      | key                  | value |
      | max_total_items      | 2     |
      | maximum_total_characters | 1000  |
      | max_items_per_source | 5     |
    And I remember the query evidence keys
    When I query with the latest run for "United States" and budget:
      | key                  | value |
      | max_total_items      | 2     |
      | offset               | 2     |
      | maximum_total_characters | 1000  |
      | max_items_per_source | 5     |
    Then the query evidence keys are disjoint from the remembered keys

  Scenario: Token chunking requires a tokenizer configuration
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 50 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I attempt to build a "embedding-index-inmemory" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                        | value |
      | chunker.chunker_id         | fixed-token-window |
      | chunker.window_tokens      | 200   |
      | chunker.overlap_tokens     | 50    |
      | embedding_provider.provider_id | hash-embedding |
      | embedding_provider.dimensions  | 32 |
    Then the command fails with exit code 2
    And standard error includes "tokenizer"

  Scenario: In-memory embedding index returns evidence
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 120 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "embedding-index-inmemory" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                            | value             |
      | snippet_characters             | 200               |
      | chunker.chunker_id             | fixed-char-window |
      | chunker.window_characters      | 800               |
      | chunker.overlap_characters     | 200               |
      | embedding_provider.provider_id | hash-embedding    |
      | embedding_provider.dimensions  | 32                |
    When I query with the latest run for "United States" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | maximum_total_characters | 1000  |
      | max_items_per_source | 5     |
    Then the query returns evidence with stage "embedding-index-inmemory"
    And the query evidence includes span offsets

  Scenario: Token chunking works when tokenizer is configured
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 120 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "embedding-index-inmemory" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                            | value              |
      | snippet_characters             | 200                |
      | chunker.chunker_id             | fixed-token-window |
      | chunker.window_tokens          | 200                |
      | chunker.overlap_tokens         | 50                 |
      | tokenizer.tokenizer_id         | whitespace         |
      | embedding_provider.provider_id | hash-embedding     |
      | embedding_provider.dimensions  | 16                 |
    When I query with the latest run for "United States" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | maximum_total_characters | 1000  |
      | max_items_per_source | 5     |
    Then the query returns evidence with stage "embedding-index-inmemory"
    And the query evidence includes span offsets

  Scenario: Embedding retrieval can build without an extraction run
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 80 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "embedding-index-file" retrieval run in corpus "corpus" with config:
      | key                            | value             |
      | snippet_characters             | 200               |
      | chunker.chunker_id             | paragraph         |
      | embedding_provider.provider_id | hash-embedding    |
      | embedding_provider.dimensions  | 32                |
    When I query with the latest run for "United States" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | maximum_total_characters | 1000  |
      | max_items_per_source | 5     |
    Then the query returns evidence with stage "embedding-index-file"

  Scenario: Query fails fast when embedding artifacts are missing
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 80 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "embedding-index-file" retrieval run in corpus "corpus" with config:
      | key                            | value             |
      | snippet_characters             | 200               |
      | chunker.chunker_id             | paragraph         |
      | embedding_provider.provider_id | hash-embedding    |
      | embedding_provider.dimensions  | 32                |
    And I delete the latest run artifacts
    When I attempt to query with the latest run for "United States" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | maximum_total_characters | 1000  |
      | max_items_per_source | 5     |
    Then the command fails with exit code 2
    And standard error includes "artifacts"

  Scenario: In-memory query fails fast when embedding artifacts are missing
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 80 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "embedding-index-inmemory" retrieval run in corpus "corpus" with config:
      | key                            | value          |
      | chunker.chunker_id             | paragraph      |
      | embedding_provider.provider_id | hash-embedding |
      | embedding_provider.dimensions  | 16             |
    And I delete the latest run artifacts
    When I attempt to query with the latest run for "United States" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | maximum_total_characters | 1000  |
      | max_items_per_source | 5     |
    Then the command fails with exit code 2
    And standard error includes "artifacts"

  Scenario: An empty embedding index returns no evidence
    Given I initialized a corpus at "corpus"
    When I build a "embedding-index-file" retrieval run in corpus "corpus" with config:
      | key                            | value          |
      | snippet_characters             | 200            |
      | chunker.chunker_id             | paragraph      |
      | embedding_provider.provider_id | hash-embedding |
      | embedding_provider.dimensions  | 16             |
    When I query with the latest run for "United States" and budget:
      | key                  | value |
      | max_total_items      | 5     |
      | maximum_total_characters | 1000  |
      | max_items_per_source | 5     |
    Then the query evidence count is 0

  Scenario: Build fails fast for unknown embedding providers
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 30 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I attempt to build a "embedding-index-file" retrieval run in corpus "corpus" with config:
      | key                            | value          |
      | chunker.chunker_id             | paragraph      |
      | embedding_provider.provider_id | not-a-provider |
      | embedding_provider.dimensions  | 16             |
    Then the command fails with exit code 2
    And standard error includes "Unknown embedding provider_id"

  Scenario: In-memory embedding index enforces maximum_cache_total_items during builds
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 80 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I attempt to build a "embedding-index-inmemory" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                            | value             |
      | chunker.chunker_id             | fixed-char-window |
      | chunker.window_characters      | 200               |
      | chunker.overlap_characters     | 0                 |
      | embedding_provider.provider_id | hash-embedding    |
      | embedding_provider.dimensions  | 16                |
      | maximum_cache_total_items                     | 1                 |
    Then the command fails with exit code 2
    And standard error includes "maximum_cache_total_items"

  Scenario: Build fails fast when a referenced extraction run is missing
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 20 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I attempt to build a "embedding-index-file" retrieval run in corpus "corpus" with config:
      | key                            | value               |
      | extraction_run                 | pass-through-text:missing-run |
      | chunker.chunker_id             | paragraph           |
      | embedding_provider.provider_id | hash-embedding      |
      | embedding_provider.dimensions  | 16                  |
    Then the command fails with exit code 2
    And standard error includes "Missing extraction run"

  Scenario: Internal chunking validators reject invalid spans and window parameters
    When I attempt to validate an invalid token span
    Then a ValueError is raised
    And the ValueError message includes "token span_end"
    When I attempt to validate an invalid text chunk
    Then a ValueError is raised
    And the ValueError message includes "chunk span_end"
    When I attempt to validate a text chunk with empty text
    Then a ValueError is raised
    And the ValueError message includes "chunk text"
    When I attempt to validate an invalid chunk record
    Then a ValueError is raised
    And the ValueError message includes "chunk span_end"
    When I attempt to construct a fixed-char-window chunker with invalid parameters
    Then a ValueError is raised
    When I attempt to construct a fixed-token-window chunker with invalid parameters
    Then a ValueError is raised
    When I attempt to construct a hash embedding provider with invalid dimensions
    Then a ValueError is raised
    When I attempt to build a tokenizer from an unknown tokenizer_id
    Then a ValueError is raised
    When I attempt to build a chunker from an unknown chunker_id
    Then a ValueError is raised
    When I attempt to build a fixed-char-window chunker without required configuration
    Then a ValueError is raised
    When I attempt to build a fixed-token-window chunker without required configuration
    Then a ValueError is raised
    When I chunk whitespace-only text with fixed window chunkers
    Then the chunk count is 0

  Scenario: Default interfaces raise clear NotImplementedError when called directly
    When I attempt to call a tokenizer base implementation
    Then a NotImplementedError is raised
    When I attempt to call a chunker base implementation
    Then a NotImplementedError is raised
    When I attempt to call an embedding provider base implementation
    Then a NotImplementedError is raised

  Scenario: Markdown front matter is stripped when loading markdown text
    When I load markdown text "doc.md" with front matter and body
    Then the loaded markdown text equals the body only

  Scenario: Chunk JSONL reader ignores blank lines
    When I write a chunks JSONL file with a blank line
    And I read the chunks JSONL file
    Then the chunk record count is 1

  Scenario: Embedding index query fails when provider returns invalid query embedding shapes
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 60 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "embedding-index-file" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                            | value             |
      | chunker.chunker_id             | fixed-char-window |
      | chunker.window_characters      | 500               |
      | chunker.overlap_characters     | 100               |
      | embedding_provider.provider_id | hash-embedding    |
      | embedding_provider.dimensions  | 32                |
    When I attempt to query backend "embedding-index-file" with an invalid query embedding shape
    Then a ValueError is raised
    And the ValueError message includes "invalid query embedding shape"

  Scenario: In-memory embedding index rejects invalid query embedding shapes
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 60 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "embedding-index-inmemory" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                            | value             |
      | chunker.chunker_id             | fixed-char-window |
      | chunker.window_characters      | 500               |
      | chunker.overlap_characters     | 100               |
      | embedding_provider.provider_id | hash-embedding    |
      | embedding_provider.dimensions  | 32                |
    When I attempt to query backend "embedding-index-inmemory" with an invalid query embedding shape
    Then a ValueError is raised
    And the ValueError message includes "invalid query embedding shape"

  Scenario: Embedding index queries fail fast on inconsistent artifacts
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 80 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "embedding-index-file" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                            | value             |
      | chunker.chunker_id             | fixed-char-window |
      | chunker.window_characters      | 400               |
      | chunker.overlap_characters     | 0                 |
      | embedding_provider.provider_id | hash-embedding    |
      | embedding_provider.dimensions  | 16                |
    When I attempt to query backend "embedding-index-file" with inconsistent artifacts
    Then a ValueError is raised
    And the ValueError message includes "inconsistent"

  Scenario: In-memory embedding index queries fail fast on inconsistent artifacts
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 80 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I build a "pass-through-text" extraction run in corpus "corpus"
    And I build a "embedding-index-inmemory" retrieval run in corpus "corpus" using the latest extraction run and config:
      | key                            | value             |
      | chunker.chunker_id             | fixed-char-window |
      | chunker.window_characters      | 400               |
      | chunker.overlap_characters     | 0                 |
      | embedding_provider.provider_id | hash-embedding    |
      | embedding_provider.dimensions  | 16                |
    When I attempt to query backend "embedding-index-inmemory" with inconsistent artifacts
    Then a ValueError is raised
    And the ValueError message includes "inconsistent"

  Scenario: Internal candidate scoring helpers handle edge cases
    When I compute top indices with an empty score array
    Then the top indices list is empty
    When I compute top indices in batches with limit 0
    Then the top indices list is empty
    When I iterate text payloads with invalid catalog items
    Then the iterated text payload count is 0
    When I collect chunks when a chunker returns no chunks
    Then the chunk count is 0
