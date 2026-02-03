Feature: Retrieval build configurations
  Retrieval builds can be configured via YAML configuration files that merge and allow CLI overrides.

  Scenario: Build uses a configuration file for retriever configuration
    Given I initialized a corpus at "corpus"
    And a WikiText-2 raw sample file "wikitext_train.txt" exists with split "train" and first 40 lines
    When I ingest the file "wikitext_train.txt" into corpus "corpus"
    And I create a retrieval build configuration file "configuration.yml" with:
      """
      snippet_characters: 200
      chunker:
        chunker_id: paragraph
      embedding_provider:
        provider_id: hash-embedding
        dimensions: 16
      """
    And I build a "embedding-index-file" retrieval snapshot in corpus "corpus" using configuration file "configuration.yml"
    Then the latest snapshot retriever id equals "embedding-index-file"
    And the latest snapshot configuration config includes "snippet_characters" with value 200
