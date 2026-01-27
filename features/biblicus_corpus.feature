Feature: Biblicus corpus (command-line interface first raw ingestion)
  Biblicus is a command-line interface first corpus for ingesting arbitrary content with minimal opinions.
  The corpus keeps raw files as the source of truth and maintains a rebuildable index.

  Scenario: Initialize a new corpus
    When I initialize a corpus at "corpus"
    Then the corpus directory "corpus" exists
    And the corpus has a config file
    And the corpus has a catalog file

  Scenario: Ingest a text note with title and tags
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello world" with title "Test" and tags "a,b" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item is a markdown note with title "Test" and tags:
      | tag |
      | a   |
      | b   |
    And the last ingested item has biblicus provenance with source "text"

  Scenario: Ingest a markdown file and merge tags
    Given I initialized a corpus at "corpus"
    And a file "note.md" exists with markdown front matter:
      | key   | value     |
      | title | From file |
      | tags  | x         |
    And the file "note.md" has body:
      """
      body line
      """
    When I ingest the file "note.md" with tags "y" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item is stored in the corpus raw folder
    And the last ingested item is markdown with title "From file" and tags:
      | tag |
      | y   |
      | x   |

  Scenario: Ingest markdown with scalar tags and existing biblicus block
    Given I initialized a corpus at "corpus"
    And a file "preset.md" exists with contents:
      """
      ---
      title: Preset
      tags: x
      biblicus:
        source: manual
      ---
      body
      """
    When I ingest the file "preset.md" with tags "x,y" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item is markdown with title "Preset" and tags:
      | tag |
      | x   |
      | y   |

  Scenario: Ingest a non-markdown file and create a sidecar
    Given I initialized a corpus at "corpus"
    And a binary file "report.pdf" exists
    When I ingest the file "report.pdf" with tags "paper" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item has a sidecar metadata file
    And the last ingested item's sidecar includes media type "application/pdf"
    And the last ingested item has biblicus provenance with a file source uniform resource identifier

  Scenario: List and show items
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "First" and tags "t1" into corpus "corpus"
    And I ingest the text "world" with title "Second" and tags "t2" into corpus "corpus"
    And I list items in corpus "corpus"
    Then the list output includes the last ingested item identifier
    When I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation includes title "Second"
    And the shown JavaScript Object Notation includes tag "t2"

  Scenario: Reindex reflects edits to sidecar metadata
    Given I initialized a corpus at "corpus"
    And a binary file "data.bin" exists
    When I ingest the file "data.bin" with tags "raw" into corpus "corpus"
    And I add tag "curated" to the last ingested item's sidecar metadata
    And I reindex corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation includes tag "raw"
    And the shown JavaScript Object Notation includes tag "curated"

  Scenario: Ingest a markdown file without front matter
    Given I initialized a corpus at "corpus"
    And a text file "plain.md" exists with contents "hello"
    When I ingest the file "plain.md" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item has biblicus provenance with a file source uniform resource identifier

  Scenario: Reindex inserts items based on universally unique identifier filename prefix
    Given I initialized a corpus at "corpus"
    And a raw file with universally unique identifier "00000000-0000-0000-0000-000000000001" exists in corpus "corpus" named "orphan.txt" with contents "hi"
    When I reindex corpus "corpus"
    Then reindex stats include inserted 1
    And reindex stats include skipped 0
