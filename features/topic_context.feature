Feature: Research agent topic context
  Biblicus generates snapshot-based Markdown context reports that summarize existing topic coverage for research agents.

  Scenario: Topic context report limits topics and chooses central representative examples
    Given I initialized a corpus at "context-lab"
    And a raw file with universally unique identifier "11111111-1111-4111-8111-111111111111" exists in corpus "context-lab" named "agent-memory.txt" with contents "agent memory planning"
    And a sidecar for raw file "11111111-1111-4111-8111-111111111111--agent-memory.txt" exists in corpus "context-lab" with Yet Another Markup Language:
      """
      title: Agent Memory
      abstract: Memory planning memory planning.
      curation:
        proposed_topic_uid: leaked-topic
      biblicus:
        id: 11111111-1111-4111-8111-111111111111
        source: urn:test:agent-memory
      """
    And a raw file with universally unique identifier "22222222-2222-4222-8222-222222222222" exists in corpus "context-lab" named "agent-tool-bridge.txt" with contents "agent memory planning tool use evaluation"
    And a sidecar for raw file "22222222-2222-4222-8222-222222222222--agent-tool-bridge.txt" exists in corpus "context-lab" with Yet Another Markup Language:
      """
      title: Agent Tool Bridge
      subtitle: Representative agent systems example
      abstract: Memory planning tool evaluation; memory planning tool evaluation.
      dates:
        published_at: "2026-01-02"
      biblicus:
        id: 22222222-2222-4222-8222-222222222222
        source: urn:test:agent-tool-bridge
      """
    And a raw file with universally unique identifier "33333333-3333-4333-8333-333333333333" exists in corpus "context-lab" named "tool-evaluation.txt" with contents "tool use evaluation"
    And a sidecar for raw file "33333333-3333-4333-8333-333333333333--tool-evaluation.txt" exists in corpus "context-lab" with Yet Another Markup Language:
      """
      title: Tool Evaluation
      abstract: Tool evaluation tool evaluation.
      biblicus:
        id: 33333333-3333-4333-8333-333333333333
        source: urn:test:tool-evaluation
      """
    And a raw file with universally unique identifier "44444444-4444-4444-8444-444444444444" exists in corpus "context-lab" named "history.txt" with contents "perceptron winter backpropagation history"
    And a sidecar for raw file "44444444-4444-4444-8444-444444444444--history.txt" exists in corpus "context-lab" with Yet Another Markup Language:
      """
      title: History
      abstract: Perceptron and backpropagation history.
      biblicus:
        id: 44444444-4444-4444-8444-444444444444
        source: urn:test:history
      """
    When I reindex corpus "context-lab"
    And I build a "metadata-text" extraction snapshot in corpus "context-lab" with config:
      | key    | value                           |
      | fields | ["title","metadata.abstract"]   |
    Given a fake BERTopic library assigns topics by document text with keywords:
      | text            | topic_id | keywords         |
      | Memory planning | 0        | agent,tool       |
      | Tool evaluation | 0        | agent,tool       |
      | Perceptron      | 1        | history,learning |
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
          nr_topics: null
      """
    When I snapshot a topic analysis in corpus "context-lab" using configuration "topic.yml" and the latest extraction snapshot
    And I generate a topic context report in corpus "context-lab" with max topics 1 and 1 example as markdown
    Then the topic context output includes 1 topic
    And the topic context Markdown includes "Agent Tool Bridge"
    And the topic context Markdown includes "Representative agent systems example"
    And the topic context Markdown includes "Memory planning tool evaluation; memory planning tool evaluation."
    And the topic context Markdown includes "urn:test:agent-tool-bridge"
    And the topic context Markdown includes "2026-01-02"
    And the topic context Markdown does not include "History"
    And the topic context Markdown does not include "leaked-topic"

  Scenario: Topic context report uses OpenAI summaries for topic guidance and missing abstracts
    Given I initialized a corpus at "summary-lab"
    And a raw file with universally unique identifier "55555555-5555-4555-8555-555555555555" exists in corpus "summary-lab" named "article.txt" with contents "This article explains automated scientific discovery systems that use agents to generate hypotheses."
    And a sidecar for raw file "55555555-5555-4555-8555-555555555555--article.txt" exists in corpus "summary-lab" with Yet Another Markup Language:
      """
      title: Discovery Article
      biblicus:
        id: 55555555-5555-4555-8555-555555555555
        source: urn:test:discovery-article
      """
    When I reindex corpus "summary-lab"
    And I build a "pass-through-text" extraction snapshot in corpus "summary-lab"
    Given a fake BERTopic library is available with topic assignments "2" and keywords:
      | topic_id | keywords              |
      | 2        | discovery,automation  |
    And a fake OpenAI library is available that returns chat completion "Research agent guidance." for prompt containing "topic context"
    And a fake OpenAI library is available that returns chat completion "One sentence article summary." for prompt containing "example summary"
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
          nr_topics: null
      """
    When I snapshot a topic analysis in corpus "summary-lab" using configuration "topic.yml" and the latest extraction snapshot
    And I generate a summarized topic context report in corpus "summary-lab" using summary model "gpt-5.4-mini" with max topics 20 and 3 examples as markdown
    Then the topic context Markdown includes "Research agent guidance."
    And the topic context Markdown includes "One sentence article summary."
    And the topic context output example "Discovery Article" uses text source "llm_summary"
