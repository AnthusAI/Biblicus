Feature: Weekly bins for topic trends
  Biblicus can bin the publication dates of each topic by ISO week so a front end can draw sparklines and trend charts.

  Background:
    Given I initialized a corpus at "weekly-lab"
    And the corpus "weekly-lab" has dated items:
      | text    | published_at |
      | agent   | 2026-01-13   |
      | agent   | 2026-01-21   |
      | agent   | 2026-01-27   |
      | agent   | 2026-02-03   |
      | agent   | 2026-02-04   |
      | agent   | 2026-02-17   |
      | agent   | 2026-03-10   |
      | agent   | 2026-03-11   |
      | science | 2026-02-10   |
      | science | 2026-03-02   |
      | science | 2026-03-20   |
      | agent   |              |
      | science |              |
    When I reindex corpus "weekly-lab"
    And I build a "pipeline" extraction snapshot in corpus "weekly-lab" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    Given a fake BERTopic library assigns topics by document text with keywords:
      | text    | topic_id | keywords             |
      | science | 1        | scientific, discovery |
      | agent   | 0        | agent, reliability    |
    And a configuration file "weekly-topic.yml" exists with content:
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
    When I snapshot a topic analysis in corpus "weekly-lab" using configuration "weekly-topic.yml" and the latest extraction snapshot

  Scenario: Request weekly bins
    When I analyze topic trends in corpus "weekly-lab" with weekly bins for 8 weeks as of "2026-03-11"
    Then the standard output validates against the published "analyze-topic-trends" response schema
    And the weekly bins list 8 ISO weeks from "2026-W04" to "2026-W11"
    And discovered topic "0" reports weekly counts "1,1,2,0,1,0,0,2"
    And discovered topic "1" reports weekly counts "0,0,0,1,0,0,1,0"

  Scenario: Longer series for a trend chart
    When I analyze topic trends in corpus "weekly-lab" with weekly bins for 26 weeks as of "2026-03-11"
    Then the weekly bins list 26 ISO weeks from "2025-W38" to "2026-W11"
    And discovered topic "0" reports 26 weekly counts that total 8

  Scenario: Items without a published date
    When I analyze topic trends in corpus "weekly-lab" with weekly bins for 8 weeks as of "2026-03-11"
    Then the weekly bins report 2 undated items
    And the weekly counts of all discovered topics total 9

  Scenario: Weekly bins default to eight weeks
    When I analyze topic trends in corpus "weekly-lab" with weekly bins and no week count as of "2026-03-11"
    Then the weekly bins list 8 ISO weeks from "2026-W04" to "2026-W11"

  Scenario: Weeks without a binning option are rejected
    When I analyze topic trends in corpus "weekly-lab" with a week count of 8 and no binning option
    Then the command fails with exit code 2
    And the failure envelope message includes "weeks"

  Scenario: Existing trailing windows unchanged
    When I analyze topic trends in corpus "weekly-lab" without a binning option as of "2026-03-11"
    Then the topic trend output has no weekly bins
    And the topic trend output has exactly the trailing-window fields
