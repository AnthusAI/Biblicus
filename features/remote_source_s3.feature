Feature: Remote S3 corpus source
  A remote S3 source mirrors objects into the corpus.

  Scenario: Pull downloads new objects from S3
    Given I initialized a corpus at "corpus"
    And the environment variable "AWS_ACCESS_KEY_ID" is set to "test-key"
    And the environment variable "AWS_SECRET_ACCESS_KEY" is set to "test-secret"
    And a remote S3 source is configured for corpus "corpus" with bucket "demo" and prefix "docs/"
    And a fake S3 source contains objects:
      | key        | content      | etag   | last_modified           |
      | docs/a.md  | Alpha note   | e1     | 2026-02-19T10:00:00Z    |
      | docs/b.md  | Beta note    | e2     | 2026-02-19T10:05:00Z    |
    When I pull the remote source for corpus "corpus"
    Then the catalog contains source uris:
      | s3://demo/docs/a.md |
      | s3://demo/docs/b.md |

  Scenario: Pull updates and prunes S3 objects
    Given I initialized a corpus at "corpus"
    And the environment variable "AWS_ACCESS_KEY_ID" is set to "test-key"
    And the environment variable "AWS_SECRET_ACCESS_KEY" is set to "test-secret"
    And a remote S3 source is configured for corpus "corpus" with bucket "demo" and prefix "docs/"
    And a fake S3 source contains objects:
      | key        | content      | etag   | last_modified           |
      | docs/a.md  | Alpha note   | e1     | 2026-02-19T10:00:00Z    |
      | docs/b.md  | Beta note    | e2     | 2026-02-19T10:05:00Z    |
    When I pull the remote source for corpus "corpus"
    And a fake S3 source contains objects:
      | key        | content        | etag   | last_modified           |
      | docs/a.md  | Alpha updated  | e1b    | 2026-02-19T11:00:00Z    |
      | docs/c.md  | Gamma note     | e3     | 2026-02-19T11:05:00Z    |
    When I pull the remote source for corpus "corpus"
    Then the catalog contains source uris:
      | s3://demo/docs/a.md |
      | s3://demo/docs/c.md |
    And the catalog does not contain source uri "s3://demo/docs/b.md"
    And the catalog item for source uri "s3://demo/docs/a.md" has biblicus source etag "e1b"

  Scenario: Local ingest is blocked when a remote source is configured
    Given I initialized a corpus at "corpus"
    And the environment variable "AWS_ACCESS_KEY_ID" is set to "test-key"
    And the environment variable "AWS_SECRET_ACCESS_KEY" is set to "test-secret"
    And a remote S3 source is configured for corpus "corpus" with bucket "demo" and prefix "docs/"
    When I ingest the text "Alpha" with no metadata into corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "remote source"

  Scenario: Missing boto3 dependency errors on pull
    Given I initialized a corpus at "corpus"
    And the boto3 dependency is unavailable
    And the environment variable "AWS_ACCESS_KEY_ID" is set to "test-key"
    And the environment variable "AWS_SECRET_ACCESS_KEY" is set to "test-secret"
    And a remote S3 source is configured for corpus "corpus" with bucket "demo" and prefix "docs/"
    When I pull the remote source for corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "boto3"
