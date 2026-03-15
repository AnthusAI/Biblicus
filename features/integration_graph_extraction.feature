@integration @neo4j
Feature: Graph extraction integration
  Graph extraction should work end-to-end against a real corpus and Neo4j.

  Scenario: Build a simple entities graph from a Wikipedia corpus
    When I download a Wikipedia corpus into "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "simple-entities" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot with real Neo4j and config:
      | key               | value |
      | min_entity_length | 3     |
    Then the graph extraction snapshot graph identifier starts with "simple-entities:"
