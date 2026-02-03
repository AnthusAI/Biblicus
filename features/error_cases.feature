Feature: Command-line interface error behavior (human-friendly failures)
  Biblicus should fail predictably and return non-zero exit codes for invalid input.

  Scenario: Ingest requires input
    Given I initialized a corpus at "corpus"
    When I snapshot "ingest" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Nothing to ingest"

  Scenario: Show fails for unknown identifier
    Given I initialized a corpus at "corpus"
    When I snapshot "show 00000000-0000-0000-0000-000000000000" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unknown item identifier"

  Scenario: List fails if the catalog file is missing
    Given I initialized a corpus at "corpus"
    And I delete the corpus catalog file in corpus "corpus"
    When I snapshot "list" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Missing corpus catalog"

  Scenario: Reject non-file corpus uniform resource identifiers
    When I snapshot "list" with corpus uniform resource identifier "http://example.com/corpus"
    Then the command fails with exit code 2
    And standard error includes "Only file:// corpus uniform resource identifiers are supported"

  Scenario: Reject file:// uniform resource identifiers with a non-local host
    When I snapshot "list" with corpus uniform resource identifier "file://example.com/tmp/corpus"
    Then the command fails with exit code 2
    And standard error includes "Unsupported file uniform resource identifier host"

  Scenario: Reject markdown with invalid Yet Another Markup Language front matter shape
    Given I initialized a corpus at "corpus"
    And a file "bad.md" exists with invalid Yet Another Markup Language front matter list
    When I ingest the file "bad.md" into corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Yet Another Markup Language front matter must be a mapping"

  Scenario: Reject markdown files that are not Unicode Transformation Format 8
    Given I initialized a corpus at "corpus"
    And a binary file "bad.md" exists with invalid Unicode Transformation Format 8 bytes
    When I ingest the file "bad.md" into corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Markdown must be Unicode Transformation Format 8"

  Scenario: Reject ingest source uniform resource locators with a non-local file:// host
    Given I initialized a corpus at "corpus"
    When I snapshot "ingest file://example.com/tmp/hello.txt" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unsupported file uniform resource identifier host"

  Scenario: Reject ingest source uniform resource locators with unsupported schemes
    Given I initialized a corpus at "corpus"
    When I snapshot "ingest ftp://example.com/hello.txt" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unsupported source uniform resource identifier scheme"

  Scenario: Sanitize unsafe filenames on ingestion
    Given I initialized a corpus at "corpus"
    And a text file "weird🔥.txt" exists with contents "x"
    When I ingest the file "weird🔥.txt" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item filename does not include "🔥"

  Scenario: Split and deduplicate tags from --tags
    Given I initialized a corpus at "corpus"
    When I ingest the text "x" with title "Tag test" and comma-tags "a, b, a" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item is a markdown note with title "Tag test" and tags:
      | tag |
      | a   |
      | b   |

  Scenario: Reject unknown retrieval retriever
    Given I initialized a corpus at "corpus"
    When I snapshot "build --retriever unknown --configuration-name default" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unknown retriever"

  Scenario: Reject invalid retriever config pairs
    Given I initialized a corpus at "corpus"
    When I snapshot "build --retriever scan --configuration-name default --config badpair" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Config values must be key=value"

  Scenario: Reject empty retriever config keys
    Given I initialized a corpus at "corpus"
    When I snapshot "build --retriever scan --configuration-name default --config =123" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Config keys must be non-empty"

  Scenario: Reject invalid chunk overlap configuration
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha bravo"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I snapshot "build --retriever sqlite-full-text-search --configuration-name default --config chunk_size=100 --config chunk_overlap=100" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "chunk_overlap must be smaller than chunk_size"

  Scenario: Reject query without a snapshot
    Given I initialized a corpus at "corpus"
    When I snapshot "query --query test --max-total-items 1 --maximum-total-characters 10 --max-items-per-source 1" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "No snapshot identifier provided"

  Scenario: Reject querying a missing snapshot manifest
    Given I initialized a corpus at "corpus"
    When I snapshot "query --snapshot 00000000-0000-0000-0000-000000000000 --query test" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Missing snapshot manifest"

  Scenario: Reject retriever mismatch on query
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "scan" retrieval snapshot in corpus "corpus"
    And I attempt to query the latest snapshot with retriever "sqlite-full-text-search"
    Then the command fails with exit code 2
    And standard error includes "Retriever mismatch"

  Scenario: Reject invalid corpus config schema version
    Given I initialized a corpus at "corpus"
    And I corrupt the corpus config schema version in corpus "corpus"
    When I snapshot "list" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unsupported corpus config schema version"

  Scenario: Reject invalid corpus catalog schema version
    Given I initialized a corpus at "corpus"
    And I corrupt the corpus catalog schema version in corpus "corpus"
    When I snapshot "list" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unsupported catalog schema version"

  Scenario: Reject invalid query budget values
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "scan" retrieval snapshot in corpus "corpus"
    And I attempt to query the latest snapshot with an invalid budget
    Then the command fails with exit code 2
    And standard error includes "greater than or equal to 1"

  Scenario: Reject evaluation queries without expectations
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "scan" retrieval snapshot in corpus "corpus"
    And I create an invalid evaluation dataset at "dataset.json" for query "alpha"
    And I attempt to evaluate the latest snapshot with dataset "dataset.json"
    Then the command fails with exit code 2
    And standard error includes "expected_item_id or expected_source_uri"

  Scenario: Reject evaluation without a snapshot
    Given I initialized a corpus at "corpus"
    And I create an empty evaluation dataset at "dataset.json"
    When I snapshot "eval --dataset dataset.json" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "No snapshot identifier provided"

  Scenario: Reject invalid dataset schema version
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "scan" retrieval snapshot in corpus "corpus"
    And I create an evaluation dataset at "dataset.json" with schema version 999
    And I attempt to evaluate the latest snapshot with dataset "dataset.json"
    Then the command fails with exit code 2
    And standard error includes "Unsupported dataset schema version"
