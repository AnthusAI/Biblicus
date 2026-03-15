Feature: Remote source helpers
  Helper functions normalize identifiers and validate configuration.

  Scenario: Normalize remote source helpers
    When I normalize a quoted remote source etag
    Then the normalized remote source etag equals "etag"
    When I normalize a remote source etag with no value
    Then the normalized remote source etag is None
    When I normalize a remote source timestamp with no value
    Then the normalized remote source timestamp is None
    When I normalize a remote source timestamp "2026-02-19T10:00:00"
    Then the normalized remote source timestamp equals "2026-02-19T10:00:00Z"

  Scenario: Iterate remote source items
    Given a fake S3 source contains objects:
      | key       | content    | etag | last_modified        |
      | docs/a.md | Alpha note | e1   | 2026-02-19T10:00:00Z |
    And a configured fake S3 remote source adapter
    When I iterate remote source items for the S3 adapter
    Then the iterated remote source item count is 1
    Given a fake Azure Blob source contains blobs:
      | name      | content    | etag | last_modified        |
      | docs/a.md | Alpha note | a1   | 2026-02-19T10:00:00Z |
    And a configured fake Azure Blob remote source adapter
    When I iterate remote source items for the Azure adapter
    Then the iterated remote source item count is 1

  Scenario: Iterating unsupported remote sources fails
    When I iterate remote source items for an unsupported adapter
    Then the remote source iteration error includes "Unsupported remote source"

  Scenario: Remote source config validation fails for unsupported kind
    When I validate a remote source config with unsupported kind
    Then the remote source validation error includes "Unsupported remote source kind"

  Scenario: Remote source config requires profile
    When I validate a remote source config without a profile
    Then the remote source validation error includes "profile"

  Scenario: Remote source config requires bucket
    When I validate a remote source config without an S3 bucket
    Then the remote source validation error includes "Remote S3 source requires bucket"

  Scenario: Remote source config requires container
    When I validate a remote source config without an Azure container
    Then the remote source validation error includes "Remote Azure Blob source requires container"
