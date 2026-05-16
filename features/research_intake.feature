Feature: Research agent intake triage
  Biblicus assesses research-agent candidates before accepting them into topic workflows.

  Background:
    Given I initialized a corpus at "intake-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "intake-lab"
    And I ingest the text "speech recognition correction model" with title "Speech Recognition" and tags "speech" into corpus "intake-lab"
    And I build a "pipeline" extraction snapshot in corpus "intake-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given a topic classifier manifest "intake-topic-classifier.json" exists for corpus "intake-lab" with topics:
      | topic_uid          | display_name       | seed_titles        | holdout_titles |
      | agent-systems      | Agent Systems      | Agent Memory       |                |
      | speech-recognition | Speech Recognition | Speech Recognition |                |
    And a topic classifier configuration "topic-classifier.yml" exists
    And a fake BERTopic library assigns topics by document text with keywords:
      | text               | topic_id | keywords          |
      | agent memory       | 0        | agent,memory      |
      | speech recognition | 1        | speech,recognize  |
    When I train a topic classifier in corpus "intake-lab" using manifest "intake-topic-classifier.json" and configuration "topic-classifier.yml"
    Given a research intake configuration "research-intake.yml" exists

  Scenario: Pre-ingest assessment accepts a candidate without changing the catalog
    Given a text file "agent-tool.txt" exists with contents "agent tool planning"
    And a metadata file "agent-tool.yml" exists with:
      """
      title: Agent Tool Planning
      abstract: agent memory retrieval planning for tool use
      """
    And fake BERTopic classification returns topic "0" with score "0.8"
    When I assess research intake candidate "agent-tool.txt" in corpus "intake-lab" with metadata file "agent-tool.yml"
    Then the command succeeds
    And the research intake decision is "accepted"
    And corpus "intake-lab" has 2 catalog items

  Scenario: Intake ingest stores accepted candidates with assessment metadata
    Given a text file "accepted-agent.txt" exists with contents "agent tool planning"
    And a metadata file "accepted-agent.yml" exists with:
      """
      title: Accepted Agent
      abstract: agent memory retrieval planning for accepted tool use
      tags:
        - ai-ml-research
      """
    And fake BERTopic classification returns topic "0" with score "0.8"
    When I research-intake ingest candidate "accepted-agent.txt" in corpus "intake-lab" with metadata file "accepted-agent.yml"
    Then the command succeeds
    And the research intake decision is "accepted"
    And the ingested research intake item has curation status "accepted"

  Scenario: Intake ingest stores pending candidates and lists them for review
    Given a text file "pending-discovery.txt" exists with contents "automated discovery"
    And a metadata file "pending-discovery.yml" exists with:
      """
      title: Pending Discovery
      abstract: autonomous laboratory hypothesis generation and automated scientific discovery
      tags:
        - ai-ml-research
      """
    And fake BERTopic classification returns topic "0" with score "0.4"
    When I research-intake ingest candidate "pending-discovery.txt" in corpus "intake-lab" with metadata file "pending-discovery.yml"
    Then the command succeeds
    And the research intake decision is "pending_review"
    And the ingested research intake item has curation status "pending_review"
    When I list pending research intake items in corpus "intake-lab" as JSON
    Then the research intake pending list includes title "Pending Discovery"
    And topic classifier manifest "intake-topic-classifier.json" does not list item titled "Pending Discovery" as a seed

  Scenario: Intake rejects irrelevant candidates without ingesting them
    Given a text file "irrelevant.txt" exists with contents "gardening soil recipes"
    And a metadata file "irrelevant.yml" exists with:
      """
      title: Gardening Notes
      abstract: soil compost and vegetable garden watering
      """
    And fake BERTopic classification returns topic "0" with score "0.1"
    When I research-intake ingest candidate "irrelevant.txt" in corpus "intake-lab" with metadata file "irrelevant.yml"
    Then the command succeeds
    And the research intake decision is "rejected"
    And corpus "intake-lab" has 2 catalog items

  Scenario: Pending and rejected items are excluded from topic modeling and classifier training
    When I ingest intake status item "Pending Item" with status "pending_review" into corpus "intake-lab"
    And I ingest intake status item "Rejected Item" with status "rejected" into corpus "intake-lab"
    And I build a "pipeline" extraction snapshot in corpus "intake-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    And I snapshot a topic analysis in corpus "intake-lab" using configuration "topic-classifier.yml" and the latest extraction snapshot
    Then the topic modeling text collection has 2 documents
    When I train a topic classifier in corpus "intake-lab" using manifest "intake-topic-classifier.json" and configuration "topic-classifier.yml"
    Then the fake BERTopic training labels contain 1 label "0", 1 label "1", and 0 labels "-1"

  Scenario: Review decisions update pending item eligibility
    When I ingest intake status item "Review Item" with status "pending_review" into corpus "intake-lab"
    And I decide research intake item titled "Review Item" in corpus "intake-lab" as "accept" with topic "agent-systems"
    Then the command succeeds
    And item titled "Review Item" in corpus "intake-lab" has curation status "accepted"
    When I decide research intake item titled "Review Item" in corpus "intake-lab" as "reject" with topic "agent-systems"
    Then the command succeeds
    And item titled "Review Item" in corpus "intake-lab" has curation status "rejected"

  Scenario: Accepting a pending item can add tags and removes it from pending review list
    When I ingest intake status item "Tag Review Item" with status "pending_review" into corpus "intake-lab"
    And I decide research intake item titled "Tag Review Item" in corpus "intake-lab" as "accept" with topic "agent-systems" adding tags ["rag", "knowledge-graph"]
    Then the command succeeds
    And item titled "Tag Review Item" in corpus "intake-lab" has curation status "accepted"
    And item titled "Tag Review Item" in corpus "intake-lab" has tags including ["rag", "knowledge-graph"]
    When I list pending research intake items in corpus "intake-lab" as JSON
    Then the research intake pending list does not include title "Tag Review Item"

  Scenario: Rejecting a pending item with delete removes its files and removes it from pending list
    When I ingest intake status item "Delete Review Item" with status "pending_review" into corpus "intake-lab"
    And I decide research intake item titled "Delete Review Item" in corpus "intake-lab" as "reject" with delete
    Then the command succeeds
    When I list pending research intake items in corpus "intake-lab" as JSON
    Then the research intake pending list does not include title "Delete Review Item"

  Scenario: Intake metadata must include title and abstract
    Given a text file "missing-abstract.txt" exists with contents "agent planning"
    And a metadata file "missing-abstract.yml" exists with:
      """
      title: Missing Abstract
      """
    When I assess research intake candidate "missing-abstract.txt" in corpus "intake-lab" with metadata file "missing-abstract.yml"
    Then the command fails with exit code 2
    And standard error includes "Research intake metadata requires field: abstract"

  Scenario: Intake metadata file must be a mapping
    Given a text file "bad-metadata.txt" exists with contents "agent planning"
    And a metadata file "bad-metadata.yml" exists with:
      """
      - not
      - a
      - mapping
      """
    When I assess research intake candidate "bad-metadata.txt" in corpus "intake-lab" with metadata file "bad-metadata.yml"
    Then the command fails with exit code 2
    And standard error includes "Ingest metadata file must be a mapping/object"
