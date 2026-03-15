Feature: Graph extraction baseline extractors
  Baseline extractors provide deterministic, non-LLM graph snapshots.

  Scenario: NER entities extractor builds a graph snapshot
    Given I initialized a corpus at "corpus"
    And a fake NLP model is installed
    When I ingest the text "Alan Turing built machines." with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "ner-entities" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key               | value           |
      | model             | en_core_web_sm |
      | min_entity_length | 3               |
      | include_item_node | true            |
    And I remember the last graph extraction snapshot reference as "ner"
    When I show graph extraction snapshot "ner" in corpus "corpus"
    Then the graph extraction snapshot graph identifier starts with "ner-entities:"

  Scenario: Dependency relations extractor builds a graph snapshot
    Given I initialized a corpus at "corpus"
    And a fake NLP model is installed
    When I ingest the text "Ada Lovelace wrote notes." with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "dependency-relations" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key               | value           |
      | model             | en_core_web_sm |
      | min_entity_length | 3               |
      | include_item_node | true            |
    And I remember the last graph extraction snapshot reference as "dependency"
    When I show graph extraction snapshot "dependency" in corpus "corpus"
    Then the graph extraction snapshot graph identifier starts with "dependency-relations:"
