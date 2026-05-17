Feature: Source-specific ingestion resolution
  Source-specific ingestion resolves platform URLs to canonical raw items and provenance.

  Scenario: DocumentCloud viewer URL stores the original Portable Document Format item
    Given I initialized a corpus at "corpus"
    And a fake public DocumentCloud document source is available
    When I ingest the fake DocumentCloud source into corpus "corpus" with import rationale "Relevant to AI and machine learning journalism because it is a primary-source court filing about automated systems in public institutions."
    Then the last ingest succeeds
    When I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation includes media type "application/pdf"
    And the shown item metadata path "curation.import_rationale" equals "Relevant to AI and machine learning journalism because it is a primary-source court filing about automated systems in public institutions."
    And the shown item metadata path "source_resolution.resolver" equals "documentcloud"
    And the shown item metadata path "source_resolution.identity_key" equals "documentcloud:27013007"
    And the shown item metadata path "documentcloud.page_count" equals 64

  Scenario: DocumentCloud aliases collide on canonical source identity
    Given I initialized a corpus at "corpus"
    And a fake public DocumentCloud document source is available
    When I ingest the fake DocumentCloud source into corpus "corpus" with import rationale "Relevant primary source."
    Then the last ingest succeeds
    When I ingest the fake DocumentCloud Portable Document Format asset into corpus "corpus"
    Then the command fails with exit code 3
    And standard error includes "matching_key: documentcloud:27013007"

  Scenario: Source-provided text extraction uses DocumentCloud full text
    Given I initialized a corpus at "corpus"
    And a fake public DocumentCloud document source is available
    When I ingest the fake DocumentCloud source into corpus "corpus" with import rationale "Relevant primary source."
    Then the last ingest succeeds
    When I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id          | config_json |
      | source-provided-text  | {}          |
      | pdf-text              | {}          |
      | select-text           | {}          |
    Then the extracted text for the last ingested item equals "DocumentCloud full text wins"
    And the extraction snapshot item provenance uses extractor "source-provided-text"

  Scenario: Non-public DocumentCloud records fail clearly
    Given I initialized a corpus at "corpus"
    And a fake private DocumentCloud document source is available
    When I attempt to ingest the fake DocumentCloud source into corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "DocumentCloud document is not public"
