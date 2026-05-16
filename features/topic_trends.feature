Feature: Temporal topic intelligence
  Biblicus ranks topic momentum from publication dates and stores topic governance proposals for review.

  Scenario: Topic trends use canonical publication dates and exclude undated items
    Given I initialized a corpus at "trend-lab"
    And a raw file with universally unique identifier "11111111-1111-4111-8111-111111111111" exists in corpus "trend-lab" named "agent-old.txt" with contents "agent reliability production monitoring"
    And a sidecar for raw file "11111111-1111-4111-8111-111111111111--agent-old.txt" exists in corpus "trend-lab" with Yet Another Markup Language:
      """
      title: Agent Old
      dates:
        published_at: "2024-01-01"
      biblicus:
        id: 11111111-1111-4111-8111-111111111111
        source: urn:test:agent-old
      """
    And a raw file with universally unique identifier "22222222-2222-4222-8222-222222222222" exists in corpus "trend-lab" named "agent-new.txt" with contents "agent reliability production evaluation"
    And a sidecar for raw file "22222222-2222-4222-8222-222222222222--agent-new.txt" exists in corpus "trend-lab" with Yet Another Markup Language:
      """
      title: Agent New
      dates:
        published_at: "2026-01-20"
      biblicus:
        id: 22222222-2222-4222-8222-222222222222
        source: urn:test:agent-new
      """
    And a raw file with universally unique identifier "33333333-3333-4333-8333-333333333333" exists in corpus "trend-lab" named "science-new.txt" with contents "automated scientific discovery agent laboratory"
    And a sidecar for raw file "33333333-3333-4333-8333-333333333333--science-new.txt" exists in corpus "trend-lab" with Yet Another Markup Language:
      """
      title: Science New
      dates:
        published_at: "2026-01-25"
      biblicus:
        id: 33333333-3333-4333-8333-333333333333
        source: urn:test:science-new
      """
    And a raw file with universally unique identifier "44444444-4444-4444-8444-444444444444" exists in corpus "trend-lab" named "undated.txt" with contents "automated scientific discovery undated"
    And a sidecar for raw file "44444444-4444-4444-8444-444444444444--undated.txt" exists in corpus "trend-lab" with Yet Another Markup Language:
      """
      title: Undated Science
      biblicus:
        id: 44444444-4444-4444-8444-444444444444
        source: urn:test:undated
      """
    When I reindex corpus "trend-lab"
    And I build a "pipeline" extraction snapshot in corpus "trend-lab" with stages:
      | extractor_id       | config_json |
      | pass-through-text  | {}          |
    Given a fake BERTopic library assigns topics by document text with keywords:
      | text       | topic_id | keywords              |
      | scientific | 1        | scientific, discovery |
      | agent      | 0        | agent, reliability    |
    And a topic classifier configuration "trend-topic-classifier.yml" exists
    And a topic classifier manifest "trend-topic-classifier.json" exists for corpus "trend-lab" with topics:
      | topic_uid     | display_name | seed_titles | holdout_titles |
      | agent-systems | Agent Systems | Agent Old   | Agent New      |
    When I train a topic classifier in corpus "trend-lab" using manifest "trend-topic-classifier.json" and configuration "trend-topic-classifier.yml"
    And I snapshot a topic analysis in corpus "trend-lab" using configuration "trend-topic-classifier.yml" and the latest extraction snapshot
    And I analyze topic trends in corpus "trend-lab" using classifier "classifier-lab-v1" with windows "30d,90d,all" as of "2026-01-31"
    Then the topic trend output excludes 1 undated item
    And the topic trend output ranks discovered topic "1" above discovered topic "0" for window "90d"
    And the topic trend output includes canonical and discovered rankings
    And the topic trend output includes a governance proposal for topic "scientific-discovery"
    And topic classifier manifest "trend-topic-classifier.json" does not include topic "scientific-discovery"

  Scenario: Legacy publication date metadata migrates to canonical dates
    Given I initialized a corpus at "date-migration-lab"
    And a raw file with universally unique identifier "55555555-5555-4555-8555-555555555555" exists in corpus "date-migration-lab" named "legacy.txt" with contents "legacy publication metadata"
    And a sidecar for raw file "55555555-5555-4555-8555-555555555555--legacy.txt" exists in corpus "date-migration-lab" with Yet Another Markup Language:
      """
      title: Legacy Date
      published: "2025-03-10"
      updated: "2025-03-11"
      biblicus:
        id: 55555555-5555-4555-8555-555555555555
        source: urn:test:legacy
      """
    When I migrate publication dates in corpus "date-migration-lab"
    And I reindex corpus "date-migration-lab"
    Then the catalog item titled "Legacy Date" has dates field "published_at" "2025-03-10"
    And the catalog item titled "Legacy Date" has dates field "updated_at" "2025-03-11"
    And the sidecar for raw file "55555555-5555-4555-8555-555555555555--legacy.txt" omits top-level metadata key "published"

  Scenario: Trend Markdown displays BERTopic labels and governance proposals use them
    Given I initialized a corpus at "trend-labels"
    And a raw file with universally unique identifier "66666666-6666-4666-8666-666666666666" exists in corpus "trend-labels" named "lab-one.txt" with contents "automated scientific discovery laboratory"
    And a sidecar for raw file "66666666-6666-4666-8666-666666666666--lab-one.txt" exists in corpus "trend-labels" with Yet Another Markup Language:
      """
      title: Lab One
      dates:
        published_at: "2026-01-20"
      biblicus:
        id: 66666666-6666-4666-8666-666666666666
        source: urn:test:lab-one
      """
    And a raw file with universally unique identifier "77777777-7777-4777-8777-777777777777" exists in corpus "trend-labels" named "lab-two.txt" with contents "automated scientific discovery agents"
    And a sidecar for raw file "77777777-7777-4777-8777-777777777777--lab-two.txt" exists in corpus "trend-labels" with Yet Another Markup Language:
      """
      title: Lab Two
      dates:
        published_at: "2026-01-25"
      biblicus:
        id: 77777777-7777-4777-8777-777777777777
        source: urn:test:lab-two
      """
    When I reindex corpus "trend-labels"
    And I build a "pipeline" extraction snapshot in corpus "trend-labels" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    Given a fake BERTopic library is available with topic assignments "2,2" and keywords:
      | topic_id | keywords              |
      | 2        | scientific,discovery  |
    And a fake OpenAI library is available that returns chat completion "Automated Discovery Systems" for any prompt
    And an OpenAI API key is configured for this scenario
    And a configuration file "topic.yml" exists with content:
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
        representation_model:
          provider: openai
          model: gpt-5.4-mini
          prompt_template: "Name this topic from [KEYWORDS] and [DOCUMENTS]."
      """
    When I snapshot a topic analysis in corpus "trend-labels" using configuration "topic.yml" and the latest extraction snapshot
    And I analyze topic trends in corpus "trend-labels" without classifier with windows "90d,all" as of "2026-01-31" as markdown
    Then the topic trend Markdown includes label "Automated Discovery Systems" for topic "2"
    And the governance proposal for topic "automated-discovery-systems" has display name "Automated Discovery Systems"
