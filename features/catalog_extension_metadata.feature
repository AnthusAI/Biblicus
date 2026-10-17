Feature: Catalog extension metadata
  Extension data from downstream tools lives under item metadata. Biblicus stores it and never interprets it.
  Catalog loading is strict, and a migration script moves legacy top-level extension fields under metadata.

  Scenario: A catalog with an unknown top-level item field fails to load
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I add the top-level catalog item field "papyrus" with value '{"category": "news"}' to the last ingested item in corpus "corpus"
    And I snapshot "list" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "unknown top-level item fields papyrus"
    And standard error includes "scripts/migrate_catalog_extensions.py"

  Scenario: A catalog with an invalid canonical item field reports the validation error
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I add the top-level catalog item field "relpath" with value '5' to the last ingested item in corpus "corpus"
    And I snapshot "list" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Invalid corpus catalog"
    And standard error includes "relpath"

  Scenario: Extension data under metadata.papyrus is preserved untouched
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I set the catalog item metadata field "papyrus" to '{"category": "news", "assignments": [1, 2]}' on the last ingested item in corpus "corpus"
    And I snapshot "list" in corpus "corpus"
    Then the command succeeds
    And the catalog item metadata field "papyrus" of the last ingested item in corpus "corpus" equals '{"category": "news", "assignments": [1, 2]}'

  Scenario: The migration script moves unknown top-level fields under metadata
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I add the top-level catalog item field "papyrus" with value '{"category": "news"}' to the last ingested item in corpus "corpus"
    And I add the top-level catalog item field "reviewed" with value 'true' to the last ingested item in corpus "corpus"
    And I run the catalog extension migration on corpus "corpus"
    Then the migration succeeds and reports "Migrated 1 item(s)"
    And the catalog item metadata field "papyrus" of the last ingested item in corpus "corpus" equals '{"category": "news"}'
    And the catalog item metadata field "reviewed" of the last ingested item in corpus "corpus" equals 'true'
    When I snapshot "list" in corpus "corpus"
    Then the command succeeds

  Scenario: The migration script merges dictionary values with existing metadata
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I set the catalog item metadata field "papyrus" to '{"category": "news", "keep": 1}' on the last ingested item in corpus "corpus"
    And I add the top-level catalog item field "papyrus" with value '{"category": "sports"}' to the last ingested item in corpus "corpus"
    And I run the catalog extension migration on corpus "corpus"
    Then the migration succeeds and reports "Migrated 1 item(s)"
    And the catalog item metadata field "papyrus" of the last ingested item in corpus "corpus" equals '{"category": "sports", "keep": 1}'

  Scenario: The migration script is idempotent
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I add the top-level catalog item field "papyrus" with value '{"category": "news"}' to the last ingested item in corpus "corpus"
    And I run the catalog extension migration on corpus "corpus"
    And I remember the catalog file content of corpus "corpus"
    And I run the catalog extension migration on corpus "corpus"
    Then the migration succeeds and reports "Migrated 0 item(s)"
    And the catalog file content of corpus "corpus" is unchanged

  Scenario: The migration dry run writes nothing
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I add the top-level catalog item field "papyrus" with value '{"category": "news"}' to the last ingested item in corpus "corpus"
    And I remember the catalog file content of corpus "corpus"
    And I run the catalog extension migration on corpus "corpus" with the dry run flag
    Then the migration succeeds and reports "Would migrate 1 item(s)"
    And the catalog file content of corpus "corpus" is unchanged
    And no temporary catalog file exists in corpus "corpus"

  Scenario: The migration writes the catalog atomically
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I add the top-level catalog item field "papyrus" with value '{"category": "news"}' to the last ingested item in corpus "corpus"
    And I run the catalog extension migration on corpus "corpus"
    Then no temporary catalog file exists in corpus "corpus"

  Scenario: Migrating an already clean catalog is a no-op
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with no metadata into corpus "corpus"
    And I remember the catalog file content of corpus "corpus"
    And I run the catalog extension migration on corpus "corpus"
    Then the migration succeeds and reports "Migrated 0 item(s)"
    And the catalog file content of corpus "corpus" is unchanged
