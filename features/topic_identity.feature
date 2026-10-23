Feature: Stable cluster identity across topic-model runs
  Biblicus matches the clusters of a topic modeling run to the clusters of the previous run by the overlap of their member items, so a consumer can say that a cluster is new, continuing, merged or split.

  Background:
    Given I initialized a corpus at "identity-lab"
    And the corpus "identity-lab" has dated items:
      | text    | published_at |
      | agent   | 2026-03-02   |
      | science | 2026-03-03   |
    When I reindex corpus "identity-lab"
    And I build a "pipeline" extraction snapshot in corpus "identity-lab" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    Given a fake BERTopic library assigns topics by document text with keywords:
      | text    | topic_id | keywords             |
      | science | 1        | scientific, discovery |
      | agent   | 0        | agent, reliability    |
    And a configuration file "identity-topic.yml" exists with content:
      """
      schema_version: 1
      text_source:
        min_text_characters: 1
      llm_extraction:
        enabled: false
      lexical_processing:
        enabled: false
      bertopic_analysis:
        parameters:
          nr_topics: 1
      """
    When I snapshot a topic analysis in corpus "identity-lab" using configuration "identity-topic.yml" and the latest extraction snapshot

  Scenario: A cluster continues
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords           |
      | 0        | 1-20  | alpha, beta        |
    And topic modeling run "run-b" in corpus "identity-lab" created "2026-09-08T00:00:00+00:00" has clusters:
      | topic_id | items | keywords           |
      | 4        | 2-21  | alpha, beta, gamma |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    And I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    Then the standard output validates against the published "analyze-topic-identity" response schema
    And cluster of topic "4" in run "run-b" has the uid of topic "0" in run "run-a"
    And cluster of topic "4" in run "run-b" has event "continued"
    And cluster of topic "4" in run "run-b" has predecessors from run "run-a" topics "0"

  Scenario: The first run has no previous run
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords    |
      | 0        | 1-20  | alpha, beta |
      | 1        | 21-30 | delta       |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    Then cluster of topic "0" in run "run-a" has event "new"
    And cluster of topic "1" in run "run-a" has event "new"
    And cluster of topic "0" in run "run-a" has a uid derived from the run identifier and topic identifier
    And run "run-a" has no previous run and no gone clusters

  Scenario: A new cluster
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords    |
      | 0        | 1-20  | alpha, beta |
    And topic modeling run "run-b" in corpus "identity-lab" created "2026-09-08T00:00:00+00:00" has clusters:
      | topic_id | items | keywords    |
      | 0        | 1-20  | alpha, beta |
      | 1        | 40-50 | delta       |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    And I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    Then cluster of topic "1" in run "run-b" has event "new"
    And cluster of topic "1" in run "run-b" has a new uid not used in run "run-a"
    And cluster of topic "1" in run "run-b" has first seen "2026-09-08"
    And cluster of topic "0" in run "run-b" has event "continued"

  Scenario: A merge
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 1-10  | alpha    |
      | 1        | 11-20 | beta     |
    And topic modeling run "run-b" in corpus "identity-lab" created "2026-09-08T00:00:00+00:00" has clusters:
      | topic_id | items | keywords    |
      | 0        | 1-20  | alpha, beta |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    And I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    Then cluster of topic "0" in run "run-b" has event "merged"
    And cluster of topic "0" in run "run-b" has predecessors from run "run-a" topics "0,1"
    And run "run-b" reports no gone clusters

  Scenario: A split
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords    |
      | 0        | 1-20  | alpha, beta |
    And topic modeling run "run-b" in corpus "identity-lab" created "2026-09-08T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 1-10  | alpha    |
      | 1        | 11-20 | beta     |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    And I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    Then cluster of topic "0" in run "run-b" has event "split"
    And cluster of topic "1" in run "run-b" has event "split"
    And cluster of topic "0" in run "run-b" has successors from run "run-b" topics "0,1"
    And cluster of topic "0" in run "run-b" has the uid of topic "0" in run "run-a"
    And cluster of topic "1" in run "run-b" has a new uid not used in run "run-a"
    And cluster of topic "1" in run "run-b" has predecessors from run "run-a" topics "0"

  Scenario: A cluster that disappears
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords    |
      | 0        | 1-20  | alpha, beta |
      | 1        | 60-70 | omega, psi  |
    And topic modeling run "run-b" in corpus "identity-lab" created "2026-09-08T00:00:00+00:00" has clusters:
      | topic_id | items | keywords    |
      | 0        | 1-20  | alpha, beta |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    And I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    Then run "run-b" reports gone clusters from run "run-a" topics "1"
    And run "run-b" event counts are "new 0, continued 1, merged 0, split 0, gone 1"

  Scenario: Matching is deterministic
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords    |
      | 0        | 1-20  | alpha, beta |
      | 1        | 21-40 | gamma       |
    And topic modeling run "run-b" in corpus "identity-lab" created "2026-09-08T00:00:00+00:00" has clusters:
      | topic_id | items | keywords    |
      | 0        | 2-21  | alpha, beta |
      | 1        | 30-50 | gamma       |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    And I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    And I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    Then the two identity reports of run "run-b" are identical

  Scenario: The threshold decides whether clusters match
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 1-20  | alpha    |
    And topic modeling run "run-b" in corpus "identity-lab" created "2026-09-08T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 11-30 | alpha    |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    And I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    Then cluster of topic "0" in run "run-b" has event "new"
    When I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.3
    Then cluster of topic "0" in run "run-b" has event "continued"

  Scenario: Identity and first seen date carry forward across runs
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 1-20  | alpha    |
    And topic modeling run "run-b" in corpus "identity-lab" created "2026-09-08T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 3        | 2-21  | alpha    |
    And topic modeling run "run-c" in corpus "identity-lab" created "2026-09-15T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 9        | 3-22  | alpha    |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    And I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    And I identify clusters of run "run-c" in corpus "identity-lab" against previous run "run-b" with threshold 0.5
    Then cluster of topic "9" in run "run-c" has the uid of topic "0" in run "run-a"
    And cluster of topic "9" in run "run-c" has first seen "2026-09-01"

  Scenario: Cluster statistics and corpus size are reported
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords                                                                  |
      | -1       | 90-95 | noise                                                                     |
      | 0        | 1-20  | k1, k2, k3, k4, k5, k6, k7, k8, k9, k10, k11, k12                         |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    Then cluster of topic "0" in run "run-a" lists 20 member items sorted by item identifier
    And cluster of topic "0" in run "run-a" has top terms "k1,k2,k3,k4,k5,k6,k7,k8,k9,k10"
    And run "run-a" reports 26 documents, 6 outlier documents and 1 cluster
    And run "run-a" has no cluster for the outlier topic

  Scenario: The previous run needs its own identity report
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 1-20  | alpha    |
    And topic modeling run "run-b" in corpus "identity-lab" created "2026-09-08T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 1-20  | alpha    |
    When I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    Then the command fails with exit code 1
    And the failure envelope message includes "Missing topic identity for previous run run-a"

  Scenario: A run cannot be its own previous run
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 1-20  | alpha    |
    When I identify clusters of run "run-a" in corpus "identity-lab" against previous run "run-a" with threshold 0.5
    Then the command fails with exit code 1
    And the failure envelope message includes "previous run must differ"

  Scenario: The threshold must be a fraction
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 1-20  | alpha    |
    When I identify clusters of run "run-a" in corpus "identity-lab" using threshold 1.5 and no previous run
    Then the command fails with exit code 2
    And the failure envelope message includes "threshold"

  Scenario: Identity as Markdown
    Given topic modeling run "run-a" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords    |
      | 0        | 1-20  | alpha, beta |
    And topic modeling run "run-b" in corpus "identity-lab" created "2026-09-08T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 5        | 2-21  | alpha    |
    When I identify clusters of run "run-a" in corpus "identity-lab" with no previous run
    And I identify clusters of run "run-b" in corpus "identity-lab" against previous run "run-a" as markdown
    Then the identity Markdown lists cluster of topic "5" in run "run-b" with event "continued"

  Scenario: Weekly series from topic trends
    When I analyze topic trends in corpus "identity-lab" with weekly bins for 8 weeks as of "2026-03-11"
    And I identify clusters of the latest topic analysis in corpus "identity-lab" with the topic trends snapshot
    Then the standard output validates against the published "analyze-topic-identity" response schema
    And the identity report lists 8 ISO weeks from "2026-W04" to "2026-W11"
    And the latest topic analysis cluster of topic "0" has weekly series "0,0,0,0,0,0,1,0"

  Scenario: Weekly series come only from the matching topic trends snapshot
    When I analyze topic trends in corpus "identity-lab" without a binning option as of "2026-03-11"
    And I identify clusters of the latest topic analysis in corpus "identity-lab" with the topic trends snapshot
    Then the command fails with exit code 1
    And the failure envelope message includes "no weekly bins"

  Scenario: Weekly series need at least eight weeks
    When I analyze topic trends in corpus "identity-lab" with weekly bins for 4 weeks as of "2026-03-11"
    And I identify clusters of the latest topic analysis in corpus "identity-lab" with the topic trends snapshot
    Then the command fails with exit code 1
    And the failure envelope message includes "at least 8 weeks"

  Scenario: Weekly series must belong to the current run
    Given topic modeling run "run-x" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 1-20  | alpha    |
    When I analyze topic trends in corpus "identity-lab" with weekly bins for 8 weeks as of "2026-03-11"
    And I identify clusters of run "run-x" in corpus "identity-lab" with the topic trends snapshot
    Then the command fails with exit code 1
    And the failure envelope message includes "not built from the current run"

  Scenario: A missing topic trends snapshot is reported
    Given topic modeling run "run-x" in corpus "identity-lab" created "2026-09-01T00:00:00+00:00" has clusters:
      | topic_id | items | keywords |
      | 0        | 1-20  | alpha    |
    When I identify clusters of run "run-x" in corpus "identity-lab" with topic trends snapshot "missing"
    Then the command fails with exit code 1
    And the failure envelope message includes "Missing topic trends output"
