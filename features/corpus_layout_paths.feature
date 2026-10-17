Feature: Corpus layout paths
  Biblicus owns the on-disk layout of a corpus. Callers ask the corpus for the location
  of the catalog, an extracted text artifact, or a graph snapshot manifest instead of
  assembling those paths themselves.

  Scenario: Corpus layout paths are resolved from identifiers without touching the disk
    Given I initialized a corpus at "corpus"
    When I open the corpus at "corpus" as a Python object
    Then the corpus catalog path is "metadata/catalog.json" under the corpus root
    And the corpus extracted text path for pipeline snapshot "snapshot-1" and item "item-1" is "extracted/pipeline/snapshot-1/text/item-1.txt" under the corpus root
    And the corpus graph snapshot manifest path for extractor "cooccurrence" and snapshot "snapshot-2" is "graph/cooccurrence/snapshot-2/manifest.json" under the corpus root

  Scenario: Corpus layout paths locate the artifacts that extraction and graph snapshots write
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha beta" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json |
      | pass-through-text | {}          |
      | select-text       | {}          |
    And I build a "cooccurrence" graph extraction snapshot in corpus "corpus" using the latest extraction snapshot and config:
      | key              | value |
      | window_size      | 3     |
      | min_cooccurrence | 1     |
    And I open the corpus at "corpus" as a Python object
    Then the corpus catalog path is a file
    And the corpus extracted text path for the last ingested item in the latest pipeline extraction snapshot contains "alpha beta"
    And the corpus graph snapshot manifest path for the last graph extraction snapshot is a file
