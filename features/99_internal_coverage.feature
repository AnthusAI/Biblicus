Feature: Internal coverage edge cases
  As a Biblicus developer
  I want core helper functions to handle edge cases predictably
  So that internal branches are fully specified and tested

  Scenario: Workflow dependency execution handles edge cases
    Given I initialized a corpus at "corpus"
    When I exercise workflow dependency edge cases
    Then the workflow dependency edge cases succeed

  Scenario: CLI dependency helpers handle edge cases
    Given I initialized a corpus at "corpus"
    When I exercise CLI dependency edge cases
    Then the CLI dependency edge cases succeed

  Scenario: Retrieval budget helpers handle offsets and caps
    When I exercise retrieval budget edge cases
    Then the retrieval budget edge cases succeed

  Scenario: Embedding provider helpers handle empty batches
    When I exercise embedding provider edge cases
    Then the embedding provider edge cases succeed

  Scenario: Snapshot reference parsing rejects malformed values
    When I exercise snapshot reference parsing edge cases
    Then the snapshot reference parsing edge cases succeed

  Scenario: Text extraction helpers handle edge cases
    When I exercise text extraction edge cases
    Then the text extraction edge cases succeed

  Scenario: Pipeline extractor config rejects nested pipeline stages
    When I exercise pipeline configuration edge cases
    Then the pipeline configuration edge cases succeed

  Scenario: Extraction snapshot handles cached manifests
    Given I initialized a corpus at "corpus"
    And a text file "note.txt" exists with contents "alpha beta"
    And a binary file "note.bin" exists with size 2 bytes
    When I exercise extraction snapshot edge cases
    Then the extraction snapshot edge cases succeed

  Scenario: Vector retriever helpers handle edge cases
    Given I initialized a corpus at "corpus"
    And a text file "note.txt" exists with contents "alpha beta"
    And a markdown file "note.md" exists with contents "---\ntitle: Note\n---\nalpha"
    When I exercise vector retriever helper edge cases
    Then the vector retriever helper edge cases succeed

  Scenario: Embedding index helpers handle edge cases
    Given I initialized a corpus at "corpus"
    And a text file "note.txt" exists with contents "alpha beta"
    When I exercise embedding index helper edge cases
    Then the embedding index helper edge cases succeed

  Scenario: SQLite retriever helpers handle edge cases
    Given I initialized a corpus at "corpus"
    And a text file "note.txt" exists with contents "alpha beta"
    When I exercise sqlite retriever helper edge cases
    Then the sqlite retriever helper edge cases succeed

  Scenario: Hybrid retriever helpers handle edge cases
    When I exercise hybrid retriever helper edge cases
    Then the hybrid retriever helper edge cases succeed

  Scenario: Graph extraction helpers handle edge cases
    When I exercise graph extraction edge cases
    Then the graph extraction edge cases succeed
