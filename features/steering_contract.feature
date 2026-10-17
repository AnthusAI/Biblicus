Feature: Steering contract toolkit
  Biblicus exposes stable JSON contracts for external application workers.

  Scenario: Export includes catalog metadata, intake statuses, topic definitions, proposals, and artifact references
    Given I initialized a corpus at "steering-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "steering-lab"
    And I ingest the text "pending automated discovery" with title "Pending Discovery" and tags "candidate" into corpus "steering-lab"
    And I ingest the text "rejected gardening note" with title "Rejected Gardening" and tags "candidate" into corpus "steering-lab"
    And item titled "Agent Memory" in corpus "steering-lab" has steering intake status "accepted"
    And item titled "Pending Discovery" in corpus "steering-lab" has steering intake status "pending_review"
    And item titled "Rejected Gardening" in corpus "steering-lab" has steering intake status "rejected"
    And I build a "pipeline" extraction snapshot in corpus "steering-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    And I build a "scan" retrieval snapshot in corpus "steering-lab"
    Given a steering topic classifier seed manifest exists in corpus "steering-lab" for classifier "steering-classifier"
    And a steering topic-governance snapshot "governance-one" exists in corpus "steering-lab"
    When I export the steering bundle for corpus "steering-lab" with classifier "steering-classifier" and governance snapshot "governance-one"
    Then the command succeeds
    And the steering export includes 3 catalog items with metadata
    And the steering export includes intake statuses "accepted,pending_review,rejected"
    And the steering export includes topic "agent-systems"
    And the steering export includes governance proposal "new-topic:automated-discovery"
    And the steering export includes artifact kind "extraction"
    And the steering export includes artifact kind "retrieval"
    And the steering export does not include raw item bytes

  Scenario: Artifact inventory is deterministic and reports missing artifact kinds
    Given I initialized a corpus at "artifact-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "artifact-lab"
    And I build a "pipeline" extraction snapshot in corpus "artifact-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    And I build a "scan" retrieval snapshot in corpus "artifact-lab"
    And a steering analysis artifact kind "topic-context" with snapshot "context-one" exists in corpus "artifact-lab"
    And a steering analysis artifact kind "topic-governance" with snapshot "governance-one" exists in corpus "artifact-lab"
    And a steering graph artifact snapshot "graph-one" exists in corpus "artifact-lab"
    When I list steering artifacts for corpus "artifact-lab"
    Then the command succeeds
    And the steering artifact inventory includes kind "extraction"
    And the steering artifact inventory includes kind "retrieval"
    And the steering artifact inventory includes kind "topic-context"
    And the steering artifact inventory includes kind "topic-governance"
    And the steering artifact inventory includes kind "graph"
    And the steering artifact inventory warns that kind "topic-classifier" is missing
    When I list steering artifacts for corpus "artifact-lab"
    Then the steering artifact inventory matches the previous inventory

  Scenario: Rendering an accepted topic set writes a strict Biblicus seed manifest
    Given a steering topic-set input "accepted-topic-set.json" exists with app-only fields
    When I render a steering seed manifest from "accepted-topic-set.json" to "seed-manifest.json"
    Then the command succeeds
    And the rendered seed manifest contains topic "agent-systems"
    And the rendered seed manifest omits app-only field "subheading"
    And the rendered seed manifest can be loaded as a Biblicus topic classifier seed manifest

  Scenario: Rendering rejects duplicate topic identifiers
    Given a malformed steering topic-set input "duplicate-topic-set.json" exists with duplicate topic identifiers
    When I attempt to render a steering seed manifest from "duplicate-topic-set.json" to "duplicate-seed-manifest.json"
    Then the command fails with exit code 2
    And standard error includes "Duplicate topic_uid"

  Scenario: Rendering rejects seed and holdout overlap
    Given a malformed steering topic-set input "overlap-topic-set.json" exists with seed holdout overlap
    When I attempt to render a steering seed manifest from "overlap-topic-set.json" to "overlap-seed-manifest.json"
    Then the command fails with exit code 2
    And standard error includes "Item cannot be both seed and holdout"

  Scenario: Rendering rejects unknown fields
    Given a malformed steering topic-set input "unknown-field-topic-set.json" exists with unknown fields
    When I attempt to render a steering seed manifest from "unknown-field-topic-set.json" to "unknown-seed-manifest.json"
    Then the command fails with exit code 2
    And standard error includes "Unknown steering topic-set fields"
