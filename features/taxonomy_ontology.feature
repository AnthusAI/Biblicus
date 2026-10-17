Feature: Taxonomy and ontology graph steering
  Biblicus validates accepted taxonomy and ontology exports, produces proposal signals, and materializes accepted state into the graph explicitly.

  Scenario: Accepted taxonomy records a strict topic tree
    Given I initialized a corpus at "taxonomy-lab"
    And an accepted taxonomy input "accepted-taxonomy.json" exists for corpus "taxonomy-lab" with root "agent-systems" and child "agent-memory"
    When I record taxonomy input "accepted-taxonomy.json" in corpus "taxonomy-lab"
    Then the command succeeds
    And the taxonomy artifact includes topic "agent-memory" under "agent-systems"

  Scenario Outline: Accepted taxonomy rejects malformed trees
    Given I initialized a corpus at "taxonomy-invalid-lab"
    And a malformed taxonomy input "bad-taxonomy.json" exists with problem "<problem>"
    When I attempt to record taxonomy input "bad-taxonomy.json" in corpus "taxonomy-invalid-lab"
    Then the command fails with exit code 2
    And standard error includes "<message>"

    Examples:
      | problem        | message              |
      | duplicate      | Duplicate topic_uid  |
      | unknown-parent | Unknown parent_topic_uid |
      | cycle          | Taxonomy cycle       |

  Scenario: Taxonomy discovery creates child-topic steering proposals without mutating the accepted taxonomy
    Given I initialized a corpus at "taxonomy-discovery-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "taxonomy-discovery-lab"
    And I ingest the text "agent persistent memory stores" with title "Memory Stores" and tags "agent" into corpus "taxonomy-discovery-lab"
    And I ingest the text "tool use planning and function calls" with title "Tool Planning" and tags "agent" into corpus "taxonomy-discovery-lab"
    And I build a "pipeline" extraction snapshot in corpus "taxonomy-discovery-lab" with stages:
      | extractor_id      |
      | pass-through-text |
    Given an accepted taxonomy input "accepted-taxonomy.json" exists for corpus "taxonomy-discovery-lab" with root "agent-systems" and child "agent-memory"
    When I record taxonomy input "accepted-taxonomy.json" in corpus "taxonomy-discovery-lab"
    Given a steering topic classifier seed manifest exists in corpus "taxonomy-discovery-lab" for classifier "steering-classifier"
    And a steering classifier topic map exists in corpus "taxonomy-discovery-lab" for classifier "steering-classifier"
    And steering classifier "steering-classifier" in corpus "taxonomy-discovery-lab" uses UMAP n_components 1
    And a fake BERTopic library assigns topics by document text with keywords:
      | text          | topic_id | keywords      |
      | memory        | 0        | memory,stores |
      | tool use      | 1        | tools,planning |
    When I discover taxonomy children in corpus "taxonomy-discovery-lab" with classifier "steering-classifier"
    Then the command succeeds
    And the taxonomy discovery output includes proposal kind "create-taxonomy-node"
    And taxonomy input "accepted-taxonomy.json" still includes 2 nodes

  Scenario: Taxonomy discovery suppresses rejected Papyrus child-topic feedback
    Given I initialized a corpus at "taxonomy-feedback-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "taxonomy-feedback-lab"
    And I ingest the text "agent persistent memory stores" with title "Memory Stores" and tags "agent" into corpus "taxonomy-feedback-lab"
    And I ingest the text "tool use planning and function calls" with title "Tool Planning" and tags "agent" into corpus "taxonomy-feedback-lab"
    And I build a "pipeline" extraction snapshot in corpus "taxonomy-feedback-lab" with stages:
      | extractor_id      |
      | pass-through-text |
    Given an accepted taxonomy input "accepted-taxonomy.json" exists for corpus "taxonomy-feedback-lab" with root "agent-systems" and child "agent-memory"
    When I record taxonomy input "accepted-taxonomy.json" in corpus "taxonomy-feedback-lab"
    Given a steering topic classifier seed manifest exists in corpus "taxonomy-feedback-lab" for classifier "steering-classifier"
    And a steering classifier topic map exists in corpus "taxonomy-feedback-lab" for classifier "steering-classifier"
    And steering classifier "steering-classifier" in corpus "taxonomy-feedback-lab" uses UMAP n_components 1
    And a fake BERTopic library assigns topics by document text with keywords:
      | text     | topic_id | keywords      |
      | memory   | 0        | memory,stores |
      | tool use | 1        | tools,planning |
    And a Papyrus steering feedback file "steering-feedback.json" suppresses proposal kind "create-taxonomy-node" under root topic "agent-systems" with display name "memory" for classifier "steering-classifier"
    When I discover taxonomy children with steering feedback "steering-feedback.json" in corpus "taxonomy-feedback-lab" with classifier "steering-classifier"
    Then the command succeeds
    And the taxonomy discovery output omits proposal display name "memory"
    And the taxonomy discovery output includes proposal display name "tools"
    And the taxonomy discovery output includes warning "Suppressed taxonomy proposal"

  Scenario: Taxonomy discovery skips scoped roots that are too small for configured UMAP
    Given I initialized a corpus at "taxonomy-small-bucket-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "taxonomy-small-bucket-lab"
    And I ingest the text "agent persistent memory stores" with title "Memory Stores" and tags "agent" into corpus "taxonomy-small-bucket-lab"
    And I build a "pipeline" extraction snapshot in corpus "taxonomy-small-bucket-lab" with stages:
      | extractor_id      |
      | pass-through-text |
    Given an accepted taxonomy input "accepted-taxonomy.json" exists for corpus "taxonomy-small-bucket-lab" with root "agent-systems" and child "agent-memory"
    When I record taxonomy input "accepted-taxonomy.json" in corpus "taxonomy-small-bucket-lab"
    Given a steering topic classifier seed manifest exists in corpus "taxonomy-small-bucket-lab" for classifier "steering-classifier"
    And a steering classifier topic map exists in corpus "taxonomy-small-bucket-lab" for classifier "steering-classifier"
    And steering classifier "steering-classifier" in corpus "taxonomy-small-bucket-lab" uses UMAP n_components 5
    When I discover taxonomy children in corpus "taxonomy-small-bucket-lab" with classifier "steering-classifier"
    Then the command succeeds
    And the taxonomy discovery output includes warning "requires at least 7 documents"
    And the taxonomy discovery output includes warning "UMAP n_components=5"

  Scenario: Taxonomy discovery skips scoped roots that are too small for BERTopic default UMAP
    Given I initialized a corpus at "taxonomy-default-umap-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "taxonomy-default-umap-lab"
    And I ingest the text "agent persistent memory stores" with title "Memory Stores" and tags "agent" into corpus "taxonomy-default-umap-lab"
    And I ingest the text "tool use planning and function calls" with title "Tool Planning" and tags "agent" into corpus "taxonomy-default-umap-lab"
    And I ingest the text "agent benchmark evaluation" with title "Agent Evaluation" and tags "agent" into corpus "taxonomy-default-umap-lab"
    And I build a "pipeline" extraction snapshot in corpus "taxonomy-default-umap-lab" with stages:
      | extractor_id      |
      | pass-through-text |
    Given an accepted taxonomy input "accepted-taxonomy.json" exists for corpus "taxonomy-default-umap-lab" with root "agent-systems" and child "agent-memory"
    When I record taxonomy input "accepted-taxonomy.json" in corpus "taxonomy-default-umap-lab"
    Given a steering topic classifier seed manifest exists in corpus "taxonomy-default-umap-lab" for classifier "steering-classifier"
    And a steering classifier topic map exists in corpus "taxonomy-default-umap-lab" for classifier "steering-classifier"
    And steering classifier "steering-classifier" in corpus "taxonomy-default-umap-lab" uses BERTopic default UMAP
    When I discover taxonomy children in corpus "taxonomy-default-umap-lab" with classifier "steering-classifier"
    Then the command succeeds
    And the taxonomy discovery output includes warning "requires at least 7 documents"
    And the taxonomy discovery output includes warning "BERTopic default UMAP n_components=5"

  Scenario: Steering proposals accept taxonomy and ontology proposal kinds
    Given a steering proposal bundle "taxonomy-ontology-proposals.json" exists with taxonomy and ontology proposals
    When I validate steering proposal bundle "taxonomy-ontology-proposals.json"
    Then the command succeeds
    And the steering proposal bundle includes proposal kinds "create-taxonomy-node,add-ontology-relationship,add-relationship-type"

  Scenario: Graph signals include missing accepted taxonomy child nodes
    Given I initialized a corpus at "taxonomy-graph-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "taxonomy-graph-lab"
    Given a steering topic classifier seed manifest exists in corpus "taxonomy-graph-lab" for classifier "steering-classifier"
    And a steering graph snapshot "graph-one" exists in corpus "taxonomy-graph-lab" with entity labels "Agent Systems"
    And an accepted taxonomy input "accepted-taxonomy.json" exists for corpus "taxonomy-graph-lab" with root "agent-systems" and child "agent-memory"
    When I record taxonomy input "accepted-taxonomy.json" in corpus "taxonomy-graph-lab"
    And I build steering graph signals for corpus "taxonomy-graph-lab" with classifier "steering-classifier" and graph snapshot "simple-entities:graph-one"
    Then the command succeeds
    And the steering signal bundle includes missing graph entity for topic "agent-memory"

  Scenario: Ontology apply materializes taxonomy and accepted relationship assertions
    Given I initialized a corpus at "ontology-apply-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "ontology-apply-lab"
    Given a steering graph snapshot "graph-one" exists in corpus "ontology-apply-lab" with entity labels "Agent Systems"
    And an accepted taxonomy input "accepted-taxonomy.json" exists for corpus "ontology-apply-lab" with root "agent-systems" and child "agent-memory"
    When I record taxonomy input "accepted-taxonomy.json" in corpus "ontology-apply-lab"
    Given an accepted ontology input "accepted-ontology.json" exists in corpus "ontology-apply-lab" linking title "Agent Memory" to topic "agent-memory"
    When I record ontology input "accepted-ontology.json" in corpus "ontology-apply-lab"
    And I apply ontology snapshot "latest" and taxonomy snapshot "latest" to graph "simple-entities:graph-one" in corpus "ontology-apply-lab"
    Then the command succeeds
    And the ontology apply output includes edge type "subtopic_of"
    And the ontology apply output includes edge type "member_of_topic"
    And the ontology apply output includes edge type "influenced"

  Scenario: Ontology query lists accepted relationships by source, relationship, and direction
    Given I initialized a corpus at "ontology-query-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "ontology-query-lab"
    Given an accepted ontology input "accepted-ontology.json" exists in corpus "ontology-query-lab" linking title "Agent Memory" to topic "agent-memory"
    When I record ontology input "accepted-ontology.json" in corpus "ontology-query-lab"
    And I query ontology relationships in corpus "ontology-query-lab" from title "Agent Memory" with relationship "influenced" and direction "outbound"
    Then the command succeeds
    And the ontology query output includes relationship "influenced" to target "topic:agent-memory"
