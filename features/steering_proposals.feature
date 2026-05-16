Feature: Unified steering proposal artifacts
  Biblicus records computational steering signals and proposal judgments without owning human decisions.

  Scenario: Graph signals include topic entities, membership edges, and topic-entity mappings
    Given I initialized a corpus at "graph-steering-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "graph-steering-lab"
    And I ingest the text "tool-using agent benchmark" with title "Tool Agents" and tags "agent" into corpus "graph-steering-lab"
    Given a steering topic classifier seed manifest exists in corpus "graph-steering-lab" for classifier "steering-classifier"
    And a steering classifier topic map exists in corpus "graph-steering-lab" for classifier "steering-classifier"
    And a steering graph snapshot "graph-one" exists in corpus "graph-steering-lab" with entity labels "Agent Systems,AI"
    When I build steering graph signals for corpus "graph-steering-lab" with classifier "steering-classifier" and graph snapshot "simple-entities:graph-one"
    Then the steering signal bundle includes signal kind "accepted-topic-missing-graph-entity"
    And the steering signal bundle includes signal kind "topic-membership-edge-candidate"
    And the steering signal bundle includes signal kind "topic-entity-name-collision"

  Scenario: Proposal bundles validate all recommendation decisions
    Given a steering proposal bundle "proposal-bundle.json" exists with recommendation decisions
    When I validate steering proposal bundle "proposal-bundle.json"
    Then the steering proposal bundle includes recommendations "recommend,do_not_recommend,needs_clarification"

  Scenario: Proposal bundles are recorded and exported without human decisions
    Given I initialized a corpus at "proposal-export-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "proposal-export-lab"
    Given a steering topic classifier seed manifest exists in corpus "proposal-export-lab" for classifier "steering-classifier"
    And a steering proposal bundle "proposal-bundle.json" exists with recommendation decisions
    When I record steering proposal bundle "proposal-bundle.json" in corpus "proposal-export-lab"
    Then a steering proposal artifact is recorded in corpus "proposal-export-lab"
    When I export the steering bundle for corpus "proposal-export-lab" with classifier "steering-classifier"
    Then the steering export includes proposal "create-topic-entity:agent-systems"
    And the steering export includes artifact kind "steering-proposals"
    And the steering export does not include human decisions

  Scenario: Human decisions are rejected from Biblicus proposal artifacts
    Given a malformed steering proposal bundle "human-decision-bundle.json" exists with human decisions
    When I attempt to validate steering proposal bundle "human-decision-bundle.json"
    Then the command fails with exit code 2
    And standard error includes "Human decisions must not be stored in Biblicus steering proposals"
