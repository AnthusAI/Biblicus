Feature: Extraction evaluation
  Extraction evaluation reports coverage and accuracy for extraction snapshots.

  Scenario: Extraction evaluation reports coverage and similarity
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I ingest the text "Beta note" with title "Beta" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create an extraction evaluation dataset "extraction_dataset.json" with expected texts:
      | expected_text |
      | Alpha note    |
      | Beta note     |
    And I evaluate extraction snapshot in corpus "corpus" using dataset "extraction_dataset.json" and the latest extraction snapshot
    Then the extraction evaluation metrics include coverage_present 2
    And the extraction evaluation metrics include coverage_empty 0
    And the extraction evaluation metrics include coverage_missing 0
    And the extraction evaluation metrics include processable_fraction 1
    And the extraction evaluation metrics include average_similarity 1

  Scenario: Extraction evaluation uses the latest extraction snapshot when omitted
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create an extraction evaluation dataset "extraction_dataset.json" with expected texts:
      | expected_text |
      | Alpha note    |
    And I evaluate extraction snapshot in corpus "corpus" using dataset "extraction_dataset.json"
    Then the command succeeds
    And standard error includes "latest extraction snapshot"

  Scenario: Extraction evaluation rejects missing dataset file
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I evaluate extraction snapshot in corpus "corpus" using dataset "missing.json" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Dataset file not found"

  Scenario: Extraction evaluation rejects invalid dataset
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create an extraction evaluation dataset file "invalid.json" with:
      """
      - not
      - a
      - mapping
      """
    And I evaluate extraction snapshot in corpus "corpus" using dataset "invalid.json" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Invalid extraction dataset"

  Scenario: Extraction evaluation reports empty and missing coverage
    Given I initialized a corpus at "corpus"
    When I ingest the text "   " with title "Blank" and tags "t" into corpus "corpus"
    And a binary file "blob.bin" exists
    And I ingest the file "blob.bin" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create an extraction evaluation dataset "extraction_dataset.json" with expected texts:
      | expected_text |
      |              |
      | blob         |
    And I evaluate extraction snapshot in corpus "corpus" using dataset "extraction_dataset.json" and the latest extraction snapshot
    Then the extraction evaluation metrics include coverage_present 0
    And the extraction evaluation metrics include coverage_empty 1
    And the extraction evaluation metrics include coverage_missing 1
    And the extraction evaluation metrics include average_similarity 0.5

  Scenario: Extraction evaluation accepts source uniform resource identifier dataset entries
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create an extraction evaluation dataset "source_dataset.json" for the last ingested item in corpus "corpus" using source uri and expected text "Alpha note"
    And I evaluate extraction snapshot in corpus "corpus" using dataset "source_dataset.json" and the latest extraction snapshot
    Then the extraction evaluation metrics include coverage_present 1
    And the extraction evaluation metrics include average_similarity 1

  Scenario: Extraction evaluation requires an extraction snapshot
    Given I initialized a corpus at "corpus"
    When I create an extraction evaluation dataset file "extraction_dataset.json" with:
      """
      {
        "schema_version": 1,
        "name": "needs-snapshot",
        "items": [
          {
            "item_id": "placeholder",
            "expected_text": "Alpha note"
          }
        ]
      }
      """
    And I evaluate extraction snapshot in corpus "corpus" using dataset "extraction_dataset.json"
    Then the command fails with exit code 2
    And standard error includes "Extraction evaluation requires an extraction snapshot"

  Scenario: Extraction evaluation rejects missing item locator
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create an extraction evaluation dataset file "missing_locator.json" with:
      """
      {
        "schema_version": 1,
        "name": "missing-locator",
        "items": [
          {
            "expected_text": "Alpha note"
          }
        ]
      }
      """
    And I evaluate extraction snapshot in corpus "corpus" using dataset "missing_locator.json" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Invalid extraction dataset"

  Scenario: Extraction evaluation rejects unsupported dataset schema version
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create an extraction evaluation dataset file "invalid_schema.json" with:
      """
      {
        "schema_version": 2,
        "name": "invalid-schema",
        "items": [
          {
            "item_id": "placeholder",
            "expected_text": "Alpha note"
          }
        ]
      }
      """
    And I evaluate extraction snapshot in corpus "corpus" using dataset "invalid_schema.json" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Invalid extraction dataset"

  Scenario: Extraction evaluation rejects unknown item identifiers
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I create an extraction evaluation dataset file "unknown_item.json" with:
      """
      {
        "schema_version": 1,
        "name": "unknown-item",
        "items": [
          {
            "item_id": "unknown",
            "expected_text": "Alpha note"
          }
        ]
      }
      """
    And I evaluate extraction snapshot in corpus "corpus" using dataset "unknown_item.json" and the latest extraction snapshot
    Then the command fails with exit code 2
    And standard error includes "Unknown item identifier"

  Scenario: Extraction evaluation resolver rejects missing locators
    When I attempt to resolve an extraction evaluation item without locators
    Then the extraction evaluation resolver error mentions "Evaluation item is missing item_id and source_uri"

  Scenario: Extraction evaluation resolver rejects unknown source uri
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I attempt to resolve an extraction evaluation item with source uri "file://missing" using catalog from corpus "corpus"
    Then the extraction evaluation resolver error mentions "Unknown source uniform resource identifier"

  Scenario: Extraction evaluation counts items added after the snapshot as missing
    Given I initialized a corpus at "corpus"
    When I ingest the text "Alpha note" with title "Alpha" and tags "t" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with steps:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
    And I ingest the text "Beta note" with title "Beta" and tags "t" into corpus "corpus"
    And I create an extraction evaluation dataset "extraction_dataset.json" with expected texts:
      | expected_text |
      | Alpha note    |
      | Beta note     |
    And I evaluate extraction snapshot in corpus "corpus" using dataset "extraction_dataset.json" and the latest extraction snapshot
    Then the extraction evaluation metrics include coverage_present 1
    And the extraction evaluation metrics include coverage_missing 1
    And the extraction evaluation metrics include processable_fraction 0.5
