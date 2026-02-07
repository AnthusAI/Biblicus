Feature: Corpus layout migration
  Legacy corpora with .biblicus/ and raw/ can be migrated to the current layout.

  Scenario: Migrate a legacy corpus layout
    Given a file "corpus/.biblicus/config.json" exists with contents:
      """
      {
        "schema_version": 2,
        "created_at": "2024-01-01T00:00:00Z",
        "corpus_uri": "file:///corpus",
        "raw_dir": "raw"
      }
      """
    And a file "corpus/.biblicus/catalog.json" exists with contents:
      """
      {
        "schema_version": 2,
        "generated_at": "2024-01-01T00:00:00Z",
        "corpus_uri": "file:///corpus",
        "raw_dir": "raw",
        "latest_run_id": null,
        "latest_snapshot_id": null,
        "items": {
          "item-1": {
            "id": "item-1",
            "relpath": "raw/alpha.txt",
            "sha256": "deadbeef",
            "bytes": 5,
            "media_type": "text/plain",
            "title": null,
            "tags": [],
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z",
            "source_uri": "file:///corpus/raw/alpha.txt"
          }
        },
        "order": ["item-1"]
      }
      """
    And a file "corpus/raw/alpha.txt" exists with contents:
      """
      alpha
      """
    When I snapshot "migrate-layout corpus" without specifying a corpus
    Then the command succeeds
    And a file "corpus/metadata/config.json" exists
    And a file "corpus/metadata/catalog.json" exists
    And a file "corpus/.biblicus/config.json" does not exist
    And a file "corpus/raw/alpha.txt" does not exist
    And a file "corpus/alpha.txt" exists
