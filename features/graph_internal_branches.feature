Feature: Graph extraction internal branches
  Graph extraction helpers should exercise error and edge cases.

  Scenario: Graph snapshot reference parsing errors
    When I parse graph snapshot reference "missing"
    Then the graph snapshot reference error is present
    When I parse graph snapshot reference "only:"
    Then the graph snapshot reference error is present
    When I serialize graph snapshot reference "ok:ref"
    Then the graph snapshot reference equals "ok:ref"

  Scenario: Graph snapshot listing skips invalid manifests
    When I list graph snapshots with invalid manifests
    Then the graph snapshot list is empty

  Scenario: Graph snapshot manifest load fails when missing
    When I load a missing graph snapshot manifest
    Then the graph extraction error is present

  Scenario: Graph snapshot listing filters by extractor
    When I create a graph snapshot manifest for extractor "cooccurrence" snapshot "snap-1"
    And I create a graph snapshot manifest for extractor "ner-entities" snapshot "snap-2"
    And I list graph snapshots for extractor "cooccurrence"
    Then the graph snapshot list includes extractor "cooccurrence"

  Scenario: Graph snapshot listing skips non-directory entries
    When I list graph snapshots with a non-directory entry
    Then the graph snapshot list is empty

  Scenario: Graph snapshot listing handles missing extractor directories
    When I list graph snapshots for extractor "missing-extractor"
    Then the graph snapshot list is empty

  Scenario: Graph snapshot references resolve
    When I create a graph snapshot manifest for extractor "cooccurrence" snapshot "snap-3"
    And I resolve the latest graph snapshot reference
    Then the latest graph snapshot reference is present
    When I resolve the graph snapshot reference "cooccurrence:snap-3"
    Then the graph snapshot reference is present

  Scenario: Graph snapshot reference is empty without snapshots
    When I resolve the latest graph snapshot reference with no snapshots
    Then the latest graph snapshot reference is absent

  Scenario: Graph extracted text loader handles missing paths
    When I load graph extracted text with missing relpath
    Then the graph extracted text is None
    When I load graph extracted text with missing file
    Then the graph extracted text is None
    When I build a graph snapshot with missing extracted text
    Then graph snapshot build succeeds

  Scenario: Graph extractors cover edge cases
    Given a fake NLP model is installed for relations
    When I extract cooccurrence graph edges from "Alpha beta"
    And I extract cooccurrence graph edges with empty text
    And I extract cooccurrence graph edges with invalid window size
    And I extract cooccurrence graph edges with high min count
    And I extract simple entity graph edges from "Alice and BOB."
    And I extract simple entity graph edges without item node
    And I extract NER graph edges from "Alice works with Bob"
    And I extract NER graph edges without item node
    And I extract dependency graph edges from "Alice writes code"
    And I extract dependency graph edges without item node
    Then graph extractor results are available

  Scenario: Graph extractors honor minimum length filters
    Given a fake NLP model is installed with short entities
    When I extract NER graph edges with minimum length 3 from "Al meets Bo"
    Then graph extractor results are available
    Given a fake NLP model is installed with short relations
    When I extract dependency graph edges with minimum length 3 from "Al writes Bo"
    Then graph extractor results are available
    When I extract dependency relations predicate without lemma from "Al writes Bo"
    Then graph extractor results are available
    Given a fake NLP model is installed for relations
    When I extract simple entity graph edges with minimum length 3 from "AI and BOB."
    Then graph extractor results are available

  Scenario: Dependency relations skip short labels
    Given a fake NLP model is installed with short relations
    When I extract dependency relations with short labels
    Then dependency relations are empty

  Scenario: Graph extractors report missing NLP dependency
    Given the NLP dependency is unavailable
    When I attempt to extract NER entities from "Alice"
    Then the graph NLP error is present
    When I attempt to extract dependency relations from "Alice writes"
    Then the graph NLP error is present

  Scenario: Graph extraction handles invalid configuration and result types
    Given a fake Neo4j driver is installed for internal checks
    When I invoke the graph extractor base validate_config
    Then the graph extraction error is present
    When I attempt to build a graph snapshot with invalid config
    Then the graph extraction error is present
    When I attempt to build a graph snapshot with invalid result type
    Then the graph extraction error is present

  Scenario: Neo4j helpers handle error branches
    When I resolve Neo4j port with invalid value
    Then the graph extraction error is present
    When I ensure Neo4j running without Docker
    Then the graph extraction error is present
    When I ensure Neo4j running with container start
    Then the graph extraction error is absent
    When I ensure Neo4j running with container run
    Then the graph extraction error is absent
    When I run a docker command that fails
    Then the graph extraction error is present
    When I wait for Neo4j availability and it times out
    Then the graph extraction error is present
    And the Neo4j timeout error includes details
    When I wait for Neo4j availability and it times out without details
    Then the graph extraction error is present
    And the Neo4j timeout error omits details
    When I create a Neo4j driver without dependency
    Then the graph extraction error is present

  Scenario: Graph extract command handles configuration and missing snapshots
    When I run the graph extract command with a configuration file
    Then the graph extraction error is absent
    When I run the graph extract command without snapshots
    Then the graph extraction error is present
