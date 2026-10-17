Feature: Ingest canonical duplicate detection
  Ingest should prevent duplicate paper items across source aliases and mirrored payloads.

  Scenario: Reingesting an arXiv paper through PDF and abstract aliases reports a canonical collision
    Given I initialized a corpus at "corpus"
    And a binary file "first.pdf" exists with Portable Document Format bytes
    And a metadata file "first.metadata.yml" exists with:
      """
      title: Darwin Godel Machine
      arxiv_id: 2505.22954v3
      """
    And a file "second.pdf" exists with bytes:
      """
      %PDF-1.7\nsecond
      """
    And a metadata file "second.metadata.yml" exists with:
      """
      title: Darwin Godel Machine Mirror
      """
    When I standard-ingest the file "first.pdf" into corpus "corpus" with metadata file "first.metadata.yml" and source uniform resource identifier "https://arxiv.org/abs/2505.22954"
    And I standard-ingest the file "second.pdf" into corpus "corpus" with metadata file "second.metadata.yml" and source uniform resource identifier "https://arxiv.org/pdf/2505.22954"
    Then the command fails with exit code 3
    And standard error includes "item already ingested"
    And standard error includes "matching_key: arxiv:2505.22954"
    And standard error includes the first ingested item id

  Scenario: Reingesting a paper through DOI aliases reports a canonical collision
    Given I initialized a corpus at "corpus"
    And a file "doi-first.pdf" exists with bytes:
      """
      %PDF-1.7\nfirst
      """
    And a metadata file "doi-first.metadata.yml" exists with:
      """
      title: DOI First
      doi: 10.1234/Example.Article
      """
    And a file "doi-second.pdf" exists with bytes:
      """
      %PDF-1.7\nsecond
      """
    And a metadata file "doi-second.metadata.yml" exists with:
      """
      title: DOI Second
      doi: https://doi.org/10.1234/example.article
      """
    When I standard-ingest the file "doi-first.pdf" into corpus "corpus" with metadata file "doi-first.metadata.yml" and source uniform resource identifier "https://doi.org/10.1234/Example.Article"
    And I standard-ingest the file "doi-second.pdf" into corpus "corpus" with metadata file "doi-second.metadata.yml" and source uniform resource identifier "https://publisher.example/articles/example"
    Then the command fails with exit code 3
    And standard error includes "item already ingested"
    And standard error includes "matching_key: doi:10.1234/example.article"
    And standard error includes the first ingested item id

  Scenario: Reingesting identical bytes from different sources reports a checksum collision
    Given I initialized a corpus at "corpus"
    And a file "bytes-first.pdf" exists with bytes:
      """
      %PDF-1.7\nsame
      """
    And a metadata file "bytes-first.metadata.yml" exists with:
      """
      title: Bytes First
      """
    And a file "bytes-second.pdf" exists with bytes:
      """
      %PDF-1.7\nsame
      """
    And a metadata file "bytes-second.metadata.yml" exists with:
      """
      title: Bytes Second
      """
    When I standard-ingest the file "bytes-first.pdf" into corpus "corpus" with metadata file "bytes-first.metadata.yml" and source uniform resource identifier "urn:source:first"
    And I standard-ingest the file "bytes-second.pdf" into corpus "corpus" with metadata file "bytes-second.metadata.yml" and source uniform resource identifier "urn:source:second"
    Then the command fails with exit code 3
    And standard error includes "item already ingested"
    And standard error includes "matching_key: sha256:"
    And standard error includes the first ingested item id

  Scenario: Distinct arXiv papers from the same source platform ingest normally
    Given I initialized a corpus at "corpus"
    And a file "distinct-first.pdf" exists with bytes:
      """
      %PDF-1.7\nfirst
      """
    And a metadata file "distinct-first.metadata.yml" exists with:
      """
      title: First Paper
      arxiv_id: 2505.22954
      """
    And a file "distinct-second.pdf" exists with bytes:
      """
      %PDF-1.7\nsecond
      """
    And a metadata file "distinct-second.metadata.yml" exists with:
      """
      title: Second Paper
      arxiv_id: 2603.18000
      """
    When I standard-ingest the file "distinct-first.pdf" into corpus "corpus" with metadata file "distinct-first.metadata.yml" and source uniform resource identifier "https://arxiv.org/abs/2505.22954"
    Then the command succeeds
    When I standard-ingest the file "distinct-second.pdf" into corpus "corpus" with metadata file "distinct-second.metadata.yml" and source uniform resource identifier "https://arxiv.org/abs/2603.18000"
    Then the command succeeds
