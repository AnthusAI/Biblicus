Feature: Python application programming interface (item-centered ingestion)
  A Python developer should be able to ingest arbitrary modality items into a corpus.

  Scenario: Ingest a binary item via the Python application programming interface
    Given I have an initialized corpus at "corpus"
    When I ingest an item via the Python application programming interface into corpus "corpus" with filename "image.png" and media type "image/png"
    Then the python ingest result succeeds
    And the python ingested item has media type "image/png"

  Scenario: Corpus has a stable file:// uniform resource identifier
    Given I have an initialized corpus at "corpus"
    When I open the corpus via the Python application programming interface at "corpus"
    Then the corpus uniform resource identifier starts with "file://"

  Scenario: Ingest a Portable Document Format file without extension has a usable filename and sidecar media type
    Given I have an initialized corpus at "corpus"
    When I ingest an item via the Python application programming interface into corpus "corpus" with filename "paper" and media type "application/pdf"
    Then the python ingest result succeeds
    And the python ingested item relpath ends with ".pdf"
    And the python ingested item sidecar includes media type "application/pdf"

  Scenario: Ingest a markdown item without extension gets .md
    Given I have an initialized corpus at "corpus"
    When I ingest an item via the Python application programming interface into corpus "corpus" with filename "note" and media type "text/markdown"
    Then the python ingest result succeeds
    And the python ingested item relpath ends with ".md"

  Scenario: Ingest an image/jpeg without extension gets .jpg
    Given I have an initialized corpus at "corpus"
    When I ingest an item via the Python application programming interface into corpus "corpus" with filename "photo" and media type "image/jpeg"
    Then the python ingest result succeeds
    And the python ingested item relpath ends with ".jpg"

  Scenario: Ingest a Portable Document Format file with no filename uses a .pdf extension
    Given I have an initialized corpus at "corpus"
    When I ingest an item via the Python application programming interface into corpus "corpus" with no filename and media type "application/pdf"
    Then the python ingest result succeeds
    And the python ingested item relpath ends with ".pdf"

  Scenario: Ingest unknown media type does not invent an extension
    Given I have an initialized corpus at "corpus"
    When I ingest an item via the Python application programming interface into corpus "corpus" with filename "mystery" and media type "application/x-biblicus-unknown"
    Then the python ingest result succeeds
    And the python ingested item relpath ends with "--mystery"
    And the python ingested item sidecar includes media type "application/x-biblicus-unknown"

  Scenario: Ingest binary metadata writes through to sidecar
    Given I have an initialized corpus at "corpus"
    When I ingest an item via the Python application programming interface with metadata foo "bar" into corpus "corpus" with filename "data.bin" and media type "application/octet-stream"
    Then the python ingest result succeeds
    And the python ingested item sidecar includes metadata foo "bar"

  Scenario: Tags ignore blanks and non-strings from front matter
    Given I have an initialized corpus at "corpus"
    When I ingest a markdown item via the Python application programming interface into corpus "corpus" with front matter tags and extra tags
    Then the python ingest result succeeds
    And the python ingested item tags equal "y,x"

  Scenario: Stream ingestion refuses Markdown
    Given I have an initialized corpus at "corpus"
    When I attempt stream ingestion of a Markdown item into corpus "corpus"
    Then the python stream ingestion error is raised

  Scenario: Stream ingestion supports no filename
    Given I have an initialized corpus at "corpus"
    When I stream ingest bytes into corpus "corpus" with no filename and media type "application/pdf"
    Then the python ingest result succeeds
    And the python ingested item relpath ends with ".pdf"

  Scenario: Stream ingestion writes metadata to sidecar
    Given I have an initialized corpus at "corpus"
    When I stream ingest bytes into corpus "corpus" with filename "blob.bin" and media type "application/octet-stream" and metadata foo "bar"
    Then the python ingest result succeeds
    And the python ingested item sidecar includes metadata foo "bar"
