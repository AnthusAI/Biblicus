Feature: Graph extraction snapshots
  Graph extraction runs after text extraction and produces a namespaced graph snapshot.
  Graph extraction is a separate pipeline stage from retrieval and analysis.

  Scenario: Unknown graph extractor is rejected
    When I attempt to resolve graph extractor "unknown-extractor"
    Then the graph extractor error mentions "Unknown graph extractor"

  Scenario: Graph extractor base class is not implemented
    When I invoke the graph extractor base class
    Then a not implemented error is raised

  Scenario: Graph extraction requires an extraction snapshot
    Given I initialized a corpus at "corpus"
    When I attempt to build a "cooccurrence" graph extraction snapshot in corpus "corpus" with extraction snapshot "pipeline:missing"
    Then the command fails with exit code 2
    And standard error includes "Missing extraction snapshot"

  Scenario: Graph extraction snapshot is idempotent for the same configuration and catalog
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha beta" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "cooccurrence" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key             | value |
      | window_size     | 3     |
      | min_cooccurrence| 1     |
    And I remember the last graph extraction snapshot reference as "first"
    And I build a "cooccurrence" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key             | value |
      | window_size     | 3     |
      | min_cooccurrence| 1     |
    Then the last graph extraction snapshot reference equals "first"

  Scenario: Graph extraction snapshot changes when the catalog changes
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "cooccurrence" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key             | value |
      | window_size     | 3     |
      | min_cooccurrence| 1     |
    And I remember the last graph extraction snapshot reference as "first"
    And I ingest the text "beta" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "cooccurrence" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key             | value |
      | window_size     | 3     |
      | min_cooccurrence| 1     |
    Then the last graph extraction snapshot reference does not equal "first"

  Scenario: Graph extraction snapshot can be listed and inspected
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha beta" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "cooccurrence" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key             | value |
      | window_size     | 3     |
      | min_cooccurrence| 1     |
    And I remember the last graph extraction snapshot reference as "first"
    When I list graph extraction snapshots in corpus "corpus"
    Then the graph extraction snapshot list includes "first"
    When I show graph extraction snapshot "first" in corpus "corpus"
    Then the shown graph extraction snapshot reference equals "first"

  Scenario: Graph extraction snapshot list is empty for a new corpus
    Given I initialized a corpus at "corpus"
    When I list graph extraction snapshots in corpus "corpus"
    Then the graph extraction snapshot list is empty

  Scenario: Graph extraction snapshot records graph identifier
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha beta" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "cooccurrence" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key             | value |
      | window_size     | 3     |
      | min_cooccurrence| 1     |
    And I remember the last graph extraction snapshot reference as "first"
    When I show graph extraction snapshot "first" in corpus "corpus"
    Then the graph extraction snapshot graph identifier starts with "cooccurrence:"

  Scenario: Graph extraction supports simple entities
    Given I initialized a corpus at "corpus"
    When I ingest the text "Ada Lovelace and Alan Turing." with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "simple-entities" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key             | value |
      | min_entity_length | 3   |
    And I remember the last graph extraction snapshot reference as "simple-entities"
    When I show graph extraction snapshot "simple-entities" in corpus "corpus"
    Then the graph extraction snapshot graph identifier starts with "simple-entities:"

  Scenario: Graph extraction auto-starts Neo4j when missing
    Given I initialized a corpus at "corpus"
    And a fake Neo4j driver is installed
    And a fake Docker daemon is installed for Neo4j
    When I ingest the text "alpha beta" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "cooccurrence" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key             | value |
      | window_size     | 3     |
      | min_cooccurrence| 1     |
    Then the Docker run command is invoked for Neo4j
