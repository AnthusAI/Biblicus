Feature: Retrieval build recipes
  Retrieval builds can be configured via YAML recipe files that merge and allow CLI overrides.

  Scenario: Build uses a recipe file for backend configuration
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 40 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I create a retrieval build recipe file "recipe.yml" with:
      """
      snippet_characters: 200
      chunker:
        chunker_id: paragraph
      embedding_provider:
        provider_id: hash-embedding
        dimensions: 16
      """
    And I build a "embedding-index-file" retrieval run in corpus "corpus" using recipe file "recipe.yml"
    Then the latest run backend id equals "embedding-index-file"
    And the latest run recipe config includes "snippet_characters" with value 200
