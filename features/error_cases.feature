Feature: Command-line interface error behavior (human-friendly failures)
  Biblicus should fail predictably and return non-zero exit codes for invalid input.

  Scenario: Ingest requires input
    Given I initialized a corpus at "corpus"
    When I run "ingest" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Nothing to ingest"

  Scenario: Show fails for unknown identifier
    Given I initialized a corpus at "corpus"
    When I run "show 00000000-0000-0000-0000-000000000000" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unknown item identifier"

  Scenario: List fails if the catalog file is missing
    Given I initialized a corpus at "corpus"
    And I delete the corpus catalog file in corpus "corpus"
    When I run "list" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Missing corpus catalog"

  Scenario: Reject non-file corpus uniform resource identifiers
    When I run "list" with corpus uniform resource identifier "http://example.com/corpus"
    Then the command fails with exit code 2
    And standard error includes "Only file:// corpus uniform resource identifiers are supported"

  Scenario: Reject file:// uniform resource identifiers with a non-local host
    When I run "list" with corpus uniform resource identifier "file://example.com/tmp/corpus"
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
    When I run "ingest file://example.com/tmp/hello.txt" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unsupported file uniform resource identifier host"

  Scenario: Reject ingest source uniform resource locators with unsupported schemes
    Given I initialized a corpus at "corpus"
    When I run "ingest ftp://example.com/hello.txt" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unsupported source uniform resource identifier scheme"

  Scenario: Sanitize unsafe filenames on ingestion
    Given I initialized a corpus at "corpus"
    And a text file "weird🔥.txt" exists with contents "x"
    When I ingest the file "weird🔥.txt" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item filename includes "--weird_.txt"

  Scenario: Split and deduplicate tags from --tags
    Given I initialized a corpus at "corpus"
    When I ingest the text "x" with title "Tag test" and comma-tags "a, b, a" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item is a markdown note with title "Tag test" and tags:
      | tag |
      | a   |
      | b   |

  Scenario: Reject unknown retrieval backend
    Given I initialized a corpus at "corpus"
    When I run "build --backend unknown --recipe-name default" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unknown backend"

  Scenario: Reject invalid backend config pairs
    Given I initialized a corpus at "corpus"
    When I run "build --backend scan --recipe-name default --config badpair" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Config values must be key=value"

  Scenario: Reject empty backend config keys
    Given I initialized a corpus at "corpus"
    When I run "build --backend scan --recipe-name default --config =123" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Config keys must be non-empty"

  Scenario: Reject invalid chunk overlap configuration
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha bravo"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I run "build --backend sqlite-full-text-search --recipe-name default --config chunk_size=100 --config chunk_overlap=100" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "chunk_overlap must be smaller than chunk_size"

  Scenario: Reject query without a run
    Given I initialized a corpus at "corpus"
    When I run "query --query test --max-total-items 1 --max-total-characters 10 --max-items-per-source 1" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "No run identifier provided"

  Scenario: Reject querying a missing run manifest
    Given I initialized a corpus at "corpus"
    When I run "query --run 00000000-0000-0000-0000-000000000000 --query test" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Missing run manifest"

  Scenario: Reject backend mismatch on query
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I attempt to query the latest run with backend "sqlite-full-text-search"
    Then the command fails with exit code 2
    And standard error includes "Backend mismatch"

  Scenario: Reject invalid corpus config schema version
    Given I initialized a corpus at "corpus"
    And I corrupt the corpus config schema version in corpus "corpus"
    When I run "list" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unsupported corpus config schema version"

  Scenario: Reject invalid corpus catalog schema version
    Given I initialized a corpus at "corpus"
    And I corrupt the corpus catalog schema version in corpus "corpus"
    When I run "list" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Unsupported catalog schema version"

  Scenario: Reject invalid query budget values
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I attempt to query the latest run with an invalid budget
    Then the command fails with exit code 2
    And standard error includes "greater than or equal to 1"

  Scenario: Reject evaluation queries without expectations
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I create an invalid evaluation dataset at "dataset.json" for query "alpha"
    And I attempt to evaluate the latest run with dataset "dataset.json"
    Then the command fails with exit code 2
    And standard error includes "expected_item_id or expected_source_uri"

  Scenario: Reject evaluation without a run
    Given I initialized a corpus at "corpus"
    And I create an empty evaluation dataset at "dataset.json"
    When I run "eval --dataset dataset.json" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "No run identifier provided"

  Scenario: Reject invalid dataset schema version
    Given I initialized a corpus at "corpus"
    And a text file "alpha.md" exists with contents "alpha"
    When I ingest the file "alpha.md" into corpus "corpus"
    And I build a "scan" retrieval run in corpus "corpus"
    And I create an evaluation dataset at "dataset.json" with schema version 999
    And I attempt to evaluate the latest run with dataset "dataset.json"
    Then the command fails with exit code 2
    And standard error includes "Unsupported dataset schema version"
