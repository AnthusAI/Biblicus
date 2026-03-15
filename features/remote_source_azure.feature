Feature: Remote Azure Blob corpus source
  A remote Azure Blob source mirrors blobs into the corpus.

  Scenario: Pull downloads new blobs from Azure
    Given I initialized a corpus at "corpus"
    And the environment variable "AZURE_STORAGE_CONNECTION_STRING" is set to "UseDevelopmentStorage=true"
    And a remote Azure Blob source is configured for corpus "corpus" with account "acct" and container "demo" and prefix "docs/"
    And a fake Azure Blob source contains blobs:
      | name       | content      | etag   | last_modified           |
      | docs/      |              |        | 2026-02-19T09:59:00Z    |
      | docs/a.md  | Alpha note   | a1     | 2026-02-19T10:00:00Z    |
      | docs/b.md  | Beta note    | b2     | 2026-02-19T10:05:00Z    |
    When I pull the remote source for corpus "corpus"
    Then the catalog contains source uris:
      | azure-blob://acct/demo/docs/a.md |
      | azure-blob://acct/demo/docs/b.md |

  Scenario: Pull updates and prunes Azure blobs
    Given I initialized a corpus at "corpus"
    And the environment variable "AZURE_STORAGE_CONNECTION_STRING" is set to "UseDevelopmentStorage=true"
    And a remote Azure Blob source is configured for corpus "corpus" with account "acct" and container "demo" and prefix "docs/"
    And a fake Azure Blob source contains blobs:
      | name       | content      | etag   | last_modified           |
      | docs/a.md  | Alpha note   | a1     | 2026-02-19T10:00:00Z    |
      | docs/b.md  | Beta note    | b2     | 2026-02-19T10:05:00Z    |
    When I pull the remote source for corpus "corpus"
    And a fake Azure Blob source contains blobs:
      | name       | content        | etag   | last_modified           |
      | docs/a.md  | Alpha updated  | a1b    | 2026-02-19T11:00:00Z    |
      | docs/c.md  | Gamma note     | c3     | 2026-02-19T11:05:00Z    |
    When I pull the remote source for corpus "corpus"
    Then the catalog contains source uris:
      | azure-blob://acct/demo/docs/a.md |
      | azure-blob://acct/demo/docs/c.md |
    And the catalog does not contain source uri "azure-blob://acct/demo/docs/b.md"
    And the catalog item for source uri "azure-blob://acct/demo/docs/a.md" has biblicus source etag "a1b"

  Scenario: Missing Azure Blob dependency errors on pull
    Given I initialized a corpus at "corpus"
    And the azure blob dependency is unavailable
    And the environment variable "AZURE_STORAGE_CONNECTION_STRING" is set to "UseDevelopmentStorage=true"
    And a remote Azure Blob source is configured for corpus "corpus" with account "acct" and container "demo" and prefix "docs/"
    When I pull the remote source for corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "azure-storage-blob"

  Scenario: Azure account key credentials use account URL
    Given I initialized a corpus at "corpus"
    And the environment variable "AZURE_STORAGE_ACCOUNT" is set to "acct"
    And the environment variable "AZURE_STORAGE_KEY" is set to "test-key"
    And a remote Azure Blob source is configured for corpus "corpus" with account "acct" and container "demo" and prefix "docs/"
    And a fake Azure Blob source contains blobs:
      | name       | content      | etag   | last_modified           | content_type |
      | docs/a.md  | Alpha note   | a1     | 2026-02-19T10:00:00Z    |             |
    When I pull the remote source for corpus "corpus"
    Then the catalog contains source uris:
      | azure-blob://acct/demo/docs/a.md |
