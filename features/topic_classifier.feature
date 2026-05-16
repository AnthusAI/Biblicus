Feature: Topic classifier workflows
  Biblicus trains classifier-style topic models from strict seed manifests.

  Scenario: AI-ML research canonical classifier excludes history articles
    Then the AI-ML research canonical topic classifier manifest does not include topic "machine-learning-history"

  Scenario: Training passes seed labels and unlabeled markers to BERTopic
    Given I initialized a corpus at "classifier-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "classifier-lab"
    And I ingest the text "speech recognition correction model" with title "Speech Recognition" and tags "speech" into corpus "classifier-lab"
    And I ingest the text "agent reliability evaluation" with title "Agent Holdout" and tags "agent" into corpus "classifier-lab"
    And I ingest the text "document layout understanding" with title "Unlabeled Document" and tags "document" into corpus "classifier-lab"
    And I build a "pipeline" extraction snapshot in corpus "classifier-lab" with stages:
      | extractor_id |
      | pass-through-text |
    Given a topic classifier manifest "topic-classifier.json" exists for corpus "classifier-lab" with topics:
      | topic_uid          | display_name       | seed_titles        | holdout_titles |
      | agent-systems      | Agent Systems      | Agent Memory       | Agent Holdout  |
      | speech-recognition | Speech Recognition | Speech Recognition |                |
    And a topic classifier configuration "topic-classifier.yml" exists
    And a fake BERTopic library is available with topic assignments "0,1,0,2" and keywords:
      | topic_id | keywords          |
      | 0        | agents,memory     |
      | 1        | speech,recognize  |
      | 2        | document,layout   |
    When I train a topic classifier in corpus "classifier-lab" using manifest "topic-classifier.json" and configuration "topic-classifier.yml"
    Then the command succeeds
    And the fake BERTopic training labels contain 1 label "0", 1 label "1", and 2 labels "-1"

  Scenario: Training labels history seeds and leaves history holdouts unlabelled
    Given I initialized a corpus at "history-classifier-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "history-classifier-lab"
    And I ingest the text "AI winters and perceptrons history" with title "AI Winters" and tags "history" into corpus "history-classifier-lab"
    And I ingest the text "Samuel checkers self play history" with title "Samuel Checkers" and tags "history" into corpus "history-classifier-lab"
    And I ingest the text "backpropagation history and attribution" with title "Backpropagation History" and tags "history" into corpus "history-classifier-lab"
    And I ingest the text "AI game playing history" with title "AI Game History" and tags "history" into corpus "history-classifier-lab"
    And I ingest the text "Breiman two cultures history" with title "Breiman Holdout" and tags "history" into corpus "history-classifier-lab"
    And I ingest the text "ImageNet benchmark history" with title "ImageNet Holdout" and tags "history" into corpus "history-classifier-lab"
    And I ingest the text "deep learning GPU history" with title "NVIDIA Holdout" and tags "history" into corpus "history-classifier-lab"
    And I ingest the text "document layout understanding" with title "Unlabeled Document" and tags "document" into corpus "history-classifier-lab"
    And I build a "pipeline" extraction snapshot in corpus "history-classifier-lab" with stages:
      | extractor_id |
      | pass-through-text |
    Given a topic classifier manifest "history-topic-classifier.json" exists for corpus "history-classifier-lab" with topics:
      | topic_uid                | display_name             | seed_titles                                                               | holdout_titles                                      |
      | agent-systems            | Agent Systems            | Agent Memory                                                              |                                                     |
      | machine-learning-history | Machine Learning History | AI Winters;Samuel Checkers;Backpropagation History;AI Game History        | Breiman Holdout;ImageNet Holdout;NVIDIA Holdout     |
    And a topic classifier configuration "topic-classifier.yml" exists
    And a fake BERTopic library is available with topic assignments "0,1,1,1,1,1,1,1,2" and keywords:
      | topic_id | keywords          |
      | 0        | agents,memory     |
      | 1        | history,learning  |
      | 2        | document,layout   |
    When I train a topic classifier in corpus "history-classifier-lab" using manifest "history-topic-classifier.json" and configuration "topic-classifier.yml"
    Then the command succeeds
    And the fake BERTopic training labels contain 1 label "0", 4 labels "1", and 4 labels "-1"

  Scenario: Manifest validation rejects duplicate topic identities
    Given I initialized a corpus at "invalid-classifier-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "invalid-classifier-lab"
    And I build a "pipeline" extraction snapshot in corpus "invalid-classifier-lab" with stages:
      | extractor_id |
      | pass-through-text |
    Given an invalid topic classifier manifest "duplicate-topic.json" exists for corpus "invalid-classifier-lab" with duplicate topic identifiers
    And a topic classifier configuration "topic-classifier.yml" exists
    And a fake BERTopic library is available
    When I train a topic classifier in corpus "invalid-classifier-lab" using manifest "duplicate-topic.json" and configuration "topic-classifier.yml"
    Then the command fails with exit code 2
    And standard error includes "Duplicate topic_uid"

  Scenario: Topic mapping records seed majority, split seed topics, and discovered topics
    Given I initialized a corpus at "mapping-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "mapping-lab"
    And I ingest the text "agent tool execution planning" with title "Agent Tools" and tags "agent" into corpus "mapping-lab"
    And I ingest the text "speech recognition correction model" with title "Speech Recognition" and tags "speech" into corpus "mapping-lab"
    And I ingest the text "document layout understanding" with title "Discovered Document" and tags "document" into corpus "mapping-lab"
    And I build a "pipeline" extraction snapshot in corpus "mapping-lab" with stages:
      | extractor_id |
      | pass-through-text |
    Given a topic classifier manifest "topic-classifier.json" exists for corpus "mapping-lab" with topics:
      | topic_uid          | display_name       | seed_titles                | holdout_titles |
      | agent-systems      | Agent Systems      | Agent Memory;Agent Tools   |                |
      | speech-recognition | Speech Recognition | Speech Recognition         |                |
    And a topic classifier configuration "topic-classifier.yml" exists
    And a fake BERTopic library assigns topics by document text with keywords:
      | text               | topic_id | keywords          |
      | agent memory       | 0        | memory,agent      |
      | agent tool         | 1        | tools,agent       |
      | speech recognition | 2        | speech,recognize  |
      | document layout    | 3        | document,layout   |
    When I train a topic classifier in corpus "mapping-lab" using manifest "topic-classifier.json" and configuration "topic-classifier.yml"
    Then the command succeeds
    And the topic classifier map links topic "agent-systems" to BERTopic topics "0,1"
    And the topic classifier map reports discovered BERTopic topic "3"

  Scenario: Classification suppresses low-confidence primary topic and returns ranked candidates
    Given I initialized a corpus at "classification-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "classification-lab"
    And I ingest the text "agent reliability evaluation" with title "Agent Reliability" and tags "agent" into corpus "classification-lab"
    And I build a "pipeline" extraction snapshot in corpus "classification-lab" with stages:
      | extractor_id |
      | pass-through-text |
    Given a topic classifier manifest "topic-classifier.json" exists for corpus "classification-lab" with topics:
      | topic_uid     | display_name  | seed_titles  | holdout_titles |
      | agent-systems | Agent Systems | Agent Memory |                |
    And a topic classifier configuration "topic-classifier.yml" exists
    And a fake BERTopic library is available with topic assignments "0,0" and keywords:
      | topic_id | keywords      |
      | 0        | agents,memory |
    And fake BERTopic classification returns topic "0" with probabilities "0:0.2"
    When I train a topic classifier in corpus "classification-lab" using manifest "topic-classifier.json" and configuration "topic-classifier.yml"
    And I classify item titled "Agent Reliability" in corpus "classification-lab" using classifier "classifier-lab-v1" with review threshold "0.5"
    Then the command succeeds
    And the topic classifier prediction has no primary topic and review_recommended "true"
    And the topic classifier prediction has ranked candidates "agent-systems"

  Scenario: Classification ranks candidates by score and limits them by top-k
    Given I initialized a corpus at "ranked-classification-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "ranked-classification-lab"
    And I ingest the text "speech recognition correction model" with title "Speech Recognition" and tags "speech" into corpus "ranked-classification-lab"
    And I ingest the text "agent reliability and speech routing" with title "Mixed Reliability" and tags "agent" into corpus "ranked-classification-lab"
    And I build a "pipeline" extraction snapshot in corpus "ranked-classification-lab" with stages:
      | extractor_id |
      | pass-through-text |
    Given a topic classifier manifest "ranked-topic-classifier.json" exists for corpus "ranked-classification-lab" with topics:
      | topic_uid          | display_name       | seed_titles        | holdout_titles |
      | agent-systems      | Agent Systems      | Agent Memory       |                |
      | speech-recognition | Speech Recognition | Speech Recognition |                |
    And a topic classifier configuration "topic-classifier.yml" exists
    And a fake BERTopic library assigns topics by document text with keywords:
      | text               | topic_id | keywords          |
      | agent memory       | 0        | agents,memory     |
      | speech recognition | 1        | speech,recognize  |
      | agent reliability  | 0        | agents,memory     |
    And fake BERTopic classification returns topic "1" with probabilities "0:0.4,1:0.8"
    When I train a topic classifier in corpus "ranked-classification-lab" using manifest "ranked-topic-classifier.json" and configuration "topic-classifier.yml"
    And I classify item titled "Mixed Reliability" in corpus "ranked-classification-lab" using classifier "classifier-lab-v1" with top-k "1" and review threshold "0.2"
    Then the command succeeds
    And the topic classifier prediction has topic_uid "speech-recognition" and review_recommended "false"
    And the topic classifier prediction has ranked candidates "speech-recognition"

  Scenario: Cross-corpus projection classifies a target item with an authority classifier
    Given I initialized a corpus at "authority-lab"
    And I initialized a corpus at "target-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "authority-lab"
    And I ingest the text "agent reliability evaluation" with title "Agent Reliability" and tags "agent" into corpus "authority-lab"
    And I build a "pipeline" extraction snapshot in corpus "authority-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given a topic classifier manifest "authority-topic-classifier.json" exists for corpus "authority-lab" with topics:
      | topic_uid     | display_name  | seed_titles  | holdout_titles |
      | agent-systems | Agent Systems | Agent Memory |                |
    And a topic classifier configuration "topic-classifier.yml" exists
    And a fake BERTopic library is available with topic assignments "0,0" and keywords:
      | topic_id | keywords      |
      | 0        | agents,memory |
    When I train a topic classifier in corpus "authority-lab" using manifest "authority-topic-classifier.json" and configuration "topic-classifier.yml"
    And I ingest the text "agent planning history article" with title "History Article" and tags "article" into corpus "target-lab"
    And I build a "pipeline" extraction snapshot in corpus "target-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given fake BERTopic classification returns topic "0" with score "0.8"
    When I project classifier "classifier-lab-v1" from corpus "authority-lab" onto item titled "History Article" in corpus "target-lab" with review threshold "0.5"
    Then the command succeeds
    And the topic classifier projection includes 1 item
    And the topic classifier projection item titled "History Article" has topic_uid "agent-systems" and review_recommended "false"

  Scenario: Cross-corpus projection records predictions in the target corpus
    Given I initialized a corpus at "record-authority-lab"
    And I initialized a corpus at "record-target-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "record-authority-lab"
    And I ingest the text "agent reliability evaluation" with title "Agent Reliability" and tags "agent" into corpus "record-authority-lab"
    And I build a "pipeline" extraction snapshot in corpus "record-authority-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given a topic classifier manifest "record-topic-classifier.json" exists for corpus "record-authority-lab" with topics:
      | topic_uid     | display_name  | seed_titles  | holdout_titles |
      | agent-systems | Agent Systems | Agent Memory |                |
    And a topic classifier configuration "record-topic-classifier.yml" exists
    And a fake BERTopic library is available with topic assignments "0,0" and keywords:
      | topic_id | keywords      |
      | 0        | agents,memory |
    When I train a topic classifier in corpus "record-authority-lab" using manifest "record-topic-classifier.json" and configuration "record-topic-classifier.yml"
    And I ingest the text "agent planning history article" with title "Recorded History Article" and tags "article" into corpus "record-target-lab"
    And I build a "pipeline" extraction snapshot in corpus "record-target-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given fake BERTopic classification returns topic "0" with score "0.9"
    When I record projection of classifier "classifier-lab-v1" from corpus "record-authority-lab" onto item titled "Recorded History Article" in corpus "record-target-lab"
    Then the command succeeds
    And the target corpus "record-target-lab" has a recorded projection for item titled "Recorded History Article" using authority corpus "record-authority-lab"
    And the target corpus "record-target-lab" recorded projection for item titled "Recorded History Article" has ranked candidates "agent-systems"
    And the authority corpus "record-authority-lab" has no recorded projection for item titled "Recorded History Article"

  Scenario: Cross-corpus projection skips unextracted items during all-item batches
    Given I initialized a corpus at "skip-authority-lab"
    And I initialized a corpus at "skip-target-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "skip-authority-lab"
    And I ingest the text "agent reliability evaluation" with title "Agent Reliability" and tags "agent" into corpus "skip-authority-lab"
    And I build a "pipeline" extraction snapshot in corpus "skip-authority-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given a topic classifier manifest "skip-topic-classifier.json" exists for corpus "skip-authority-lab" with topics:
      | topic_uid     | display_name  | seed_titles  | holdout_titles |
      | agent-systems | Agent Systems | Agent Memory |                |
    And a topic classifier configuration "skip-topic-classifier.yml" exists
    And a fake BERTopic library is available with topic assignments "0,0" and keywords:
      | topic_id | keywords      |
      | 0        | agents,memory |
    When I train a topic classifier in corpus "skip-authority-lab" using manifest "skip-topic-classifier.json" and configuration "skip-topic-classifier.yml"
    And I ingest the text "agent planning history article" with title "Extracted History Article" and tags "article" into corpus "skip-target-lab"
    And I build a "pipeline" extraction snapshot in corpus "skip-target-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    And I ingest the text "agent planning without extracted text" with title "Unextracted History Article" and tags "article" into corpus "skip-target-lab"
    Given fake BERTopic classification returns topic "0" with score "0.9"
    When I project classifier "classifier-lab-v1" from corpus "skip-authority-lab" onto all items in corpus "skip-target-lab"
    Then the command succeeds
    And the topic classifier projection includes 1 item
    And the topic classifier projection skips 1 item
    And the topic classifier projection skipped item titled "Unextracted History Article" reason includes "Missing extracted text"

  Scenario: Cross-corpus projection accepts repeated item identifiers
    Given I initialized a corpus at "repeat-authority-lab"
    And I initialized a corpus at "repeat-target-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "repeat-authority-lab"
    And I ingest the text "agent reliability evaluation" with title "Agent Reliability" and tags "agent" into corpus "repeat-authority-lab"
    And I build a "pipeline" extraction snapshot in corpus "repeat-authority-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given a topic classifier manifest "repeat-topic-classifier.json" exists for corpus "repeat-authority-lab" with topics:
      | topic_uid     | display_name  | seed_titles  | holdout_titles |
      | agent-systems | Agent Systems | Agent Memory |                |
    And a topic classifier configuration "repeat-topic-classifier.yml" exists
    And a fake BERTopic library is available with topic assignments "0,0" and keywords:
      | topic_id | keywords      |
      | 0        | agents,memory |
    When I train a topic classifier in corpus "repeat-authority-lab" using manifest "repeat-topic-classifier.json" and configuration "repeat-topic-classifier.yml"
    And I ingest the text "agent planning first article" with title "First History Article" and tags "article" into corpus "repeat-target-lab"
    And I ingest the text "agent planning second article" with title "Second History Article" and tags "article" into corpus "repeat-target-lab"
    And I build a "pipeline" extraction snapshot in corpus "repeat-target-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given fake BERTopic classification returns topic "0" with score "0.9"
    When I project classifier "classifier-lab-v1" from corpus "repeat-authority-lab" onto items titled "First History Article;Second History Article" in corpus "repeat-target-lab"
    Then the command succeeds
    And the topic classifier projection includes 2 items
    And the topic classifier projection skips 0 items

  Scenario: Cross-corpus projection markdown includes ranked candidates
    Given I initialized a corpus at "markdown-authority-lab"
    And I initialized a corpus at "markdown-target-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "markdown-authority-lab"
    And I ingest the text "speech recognition correction model" with title "Speech Recognition" and tags "speech" into corpus "markdown-authority-lab"
    And I build a "pipeline" extraction snapshot in corpus "markdown-authority-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given a topic classifier manifest "markdown-topic-classifier.json" exists for corpus "markdown-authority-lab" with topics:
      | topic_uid          | display_name       | seed_titles        | holdout_titles |
      | agent-systems      | Agent Systems      | Agent Memory       |                |
      | speech-recognition | Speech Recognition | Speech Recognition |                |
    And a topic classifier configuration "markdown-topic-classifier.yml" exists
    And a fake BERTopic library assigns topics by document text with keywords:
      | text               | topic_id | keywords          |
      | agent memory       | 0        | agents,memory     |
      | speech recognition | 1        | speech,recognize  |
    When I train a topic classifier in corpus "markdown-authority-lab" using manifest "markdown-topic-classifier.json" and configuration "markdown-topic-classifier.yml"
    And I ingest the text "agent and speech history article" with title "Markdown History Article" and tags "article" into corpus "markdown-target-lab"
    And I build a "pipeline" extraction snapshot in corpus "markdown-target-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given fake BERTopic classification returns topic "1" with probabilities "0:0.4,1:0.8"
    When I project classifier "classifier-lab-v1" from corpus "markdown-authority-lab" onto item titled "Markdown History Article" in corpus "markdown-target-lab" as markdown with top-k "2"
    Then the command succeeds
    And standard output includes "Candidates"
    And standard output includes "speech-recognition 0.800"
    And standard output includes "agent-systems 0.400"

  Scenario: Cross-corpus projection rejects ambiguous selection
    Given I initialized a corpus at "ambiguous-authority-lab"
    And I initialized a corpus at "ambiguous-target-lab"
    When I project classifier "classifier-lab-v1" from corpus "ambiguous-authority-lab" onto all items and item id "example-item" in corpus "ambiguous-target-lab"
    Then the command fails with exit code 2
    And standard error includes "Topic classifier projection requires exactly one of --all or --item-id"

  Scenario: Cross-corpus projection requires a target extraction snapshot
    Given I initialized a corpus at "missing-snapshot-authority-lab"
    And I initialized a corpus at "missing-snapshot-target-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "missing-snapshot-authority-lab"
    And I ingest the text "agent reliability evaluation" with title "Agent Reliability" and tags "agent" into corpus "missing-snapshot-authority-lab"
    And I build a "pipeline" extraction snapshot in corpus "missing-snapshot-authority-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    Given a topic classifier manifest "missing-snapshot-topic-classifier.json" exists for corpus "missing-snapshot-authority-lab" with topics:
      | topic_uid     | display_name  | seed_titles  | holdout_titles |
      | agent-systems | Agent Systems | Agent Memory |                |
    And a topic classifier configuration "missing-snapshot-topic-classifier.yml" exists
    And a fake BERTopic library is available with topic assignments "0,0" and keywords:
      | topic_id | keywords      |
      | 0        | agents,memory |
    When I train a topic classifier in corpus "missing-snapshot-authority-lab" using manifest "missing-snapshot-topic-classifier.json" and configuration "missing-snapshot-topic-classifier.yml"
    And I ingest the text "agent planning history article" with title "Missing Snapshot History Article" and tags "article" into corpus "missing-snapshot-target-lab"
    And I project classifier "classifier-lab-v1" from corpus "missing-snapshot-authority-lab" onto item titled "Missing Snapshot History Article" in corpus "missing-snapshot-target-lab" with missing extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Missing extraction snapshot manifest"

  Scenario: Blind candidate batch review classifies items and summarizes discovery
    Given I initialized a corpus at "review-lab"
    And a text file "ai-scientist.txt" exists with contents "automated scientific discovery agentic research"
    And a metadata file "ai-scientist.yml" exists with:
      """
      title: AI Scientist
      tags:
        - ai-ml-research
        - automated-scientific-discovery-candidate
      curation:
        proposed_topic_uid: automated-scientific-discovery
      """
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "review-lab"
    And I standard-ingest the file "ai-scientist.txt" into corpus "review-lab" with metadata file "ai-scientist.yml" and source uniform resource identifier "https://example.test/ai-scientist"
    And I build a "pipeline" extraction snapshot in corpus "review-lab" with stages:
      | extractor_id |
      | pass-through-text |
    Given a topic classifier manifest "review-topic-classifier.json" exists for corpus "review-lab" with topics:
      | topic_uid     | display_name  | seed_titles  | holdout_titles |
      | agent-systems | Agent Systems | Agent Memory |                |
    And a topic classifier configuration "topic-classifier.yml" exists
    And a fake BERTopic library assigns topics by document text with keywords:
      | text                           | topic_id | keywords             |
      | agent memory                   | 0        | agent,memory         |
      | automated scientific discovery | 3        | discovery,research   |
    When I train a topic classifier in corpus "review-lab" using manifest "review-topic-classifier.json" and configuration "topic-classifier.yml"
    And I snapshot a topic analysis in corpus "review-lab" using configuration "topic-classifier.yml" and the latest extraction snapshot
    And I review candidate items in corpus "review-lab" using classifier "classifier-lab-v1" with candidate tag "automated-scientific-discovery-candidate" and proposed topic "automated-scientific-discovery"
    Then the command succeeds
    And the topic classifier batch review includes 1 candidate item
    And the topic classifier batch review item titled "AI Scientist" has proposed topic "automated-scientific-discovery" and unsupervised topic "3"
    And the topic classifier batch review summary flag "candidate_topic_reached_review_size" is "false"
    And topic classifier manifest "review-topic-classifier.json" does not list item titled "AI Scientist" as a seed

  Scenario: Reviewed candidates can draft a new manifest without mutating the baseline
    Given I initialized a corpus at "draft-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "draft-lab"
    And I ingest the text "automated scientific discovery agentic research" with title "AI Scientist" and tags "automated-scientific-discovery-candidate" into corpus "draft-lab"
    And I build a "pipeline" extraction snapshot in corpus "draft-lab" with stages:
      | extractor_id |
      | pass-through-text |
    Given a topic classifier manifest "base-topic-classifier.json" exists for corpus "draft-lab" with topics:
      | topic_uid     | display_name  | seed_titles  | holdout_titles |
      | agent-systems | Agent Systems | Agent Memory |                |
    When I draft topic classifier manifest "draft-topic-classifier.json" from "base-topic-classifier.json" with topic "automated-scientific-discovery" using seed title "AI Scientist"
    Then the command succeeds
    And topic classifier manifest "draft-topic-classifier.json" includes topic "automated-scientific-discovery"
    And topic classifier manifest "base-topic-classifier.json" does not include topic "automated-scientific-discovery"
