Feature: Ingest namespacing preserves source uniqueness
  Ingested items are stored under filenames derived from their full source uniform resource
  identifiers to prevent collisions between identical basenames.

  Scenario: Hypertext transfer protocol sources are percent-encoded
    Given I initialized a corpus at "corpus"
    And a hypertext transfer protocol server is serving the workdir
    And a text file "alpha/README.md" exists with contents "alpha"
    And a text file "beta/README.md" exists with contents "beta"
    When I ingest the hypertext transfer protocol uniform resource locator for "alpha/README.md" into corpus "corpus"
    And I ingest the hypertext transfer protocol uniform resource locator for "beta/README.md" into corpus "corpus"
    Then the ingested relpaths are distinct
    And each ingested relpath includes the percent-encoded source uniform resource identifier

  Scenario: File sources are percent-encoded
    Given I initialized a corpus at "corpus"
    And a text file "dir_one/README.md" exists with contents "first"
    And a text file "dir_two/README.md" exists with contents "second"
    When I ingest the file "dir_one/README.md" into corpus "corpus"
    And I ingest the file "dir_two/README.md" into corpus "corpus"
    Then the ingested relpaths are distinct
    And each ingested relpath includes the percent-encoded source uniform resource identifier

  Scenario: Reingesting a hypertext transfer protocol source reports a collision
    Given I initialized a corpus at "corpus"
    And a hypertext transfer protocol server is serving the workdir
    And a text file "dup/README.md" exists with contents "duplicate"
    When I ingest the hypertext transfer protocol uniform resource locator for "dup/README.md" into corpus "corpus"
    And I ingest the hypertext transfer protocol uniform resource locator for "dup/README.md" into corpus "corpus"
    Then the command fails with exit code 3
    And standard error includes "source already ingested"
    And standard error includes the last source uniform resource identifier
    And standard error includes the first ingested item id

  Scenario: Reingesting a file source reports a collision
    Given I initialized a corpus at "corpus"
    And a text file "localdup/README.md" exists with contents "local"
    When I ingest the file "localdup/README.md" into corpus "corpus"
    And I ingest the file "localdup/README.md" into corpus "corpus"
    Then the command fails with exit code 3
    And standard error includes "source already ingested"
    And standard error includes the last source uniform resource identifier
    And standard error includes the first ingested item id
