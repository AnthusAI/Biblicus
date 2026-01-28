Feature: Content sniffing for media type and filename extension
  When a source provides no usable media type header and no filename extension, Biblicus should identify common formats.

  Scenario: Hypertext transfer protocol ingest uses sniffed media type when content type header is missing
    Given I initialized a corpus at "corpus"
    And a binary file "download" exists with Portable Document Format bytes
    And a hypertext transfer protocol server is serving the workdir without content type headers
    When I ingest the hypertext transfer protocol uniform resource locator for "download" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item relpath ends with ".pdf"
    And the last ingested item's sidecar includes media type "application/pdf"

  Scenario: Hypertext transfer protocol ingest sniffs hypertext markup language
    Given I initialized a corpus at "corpus"
    And a file "download" exists with bytes:
      """
      <!doctype html><html><body>hello</body></html>
      """
    And a hypertext transfer protocol server is serving the workdir without content type headers
    When I ingest the hypertext transfer protocol uniform resource locator for "download" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item relpath ends with ".html"

  Scenario: Hypertext transfer protocol ingest sniffs portable network graphics
    Given I initialized a corpus at "corpus"
    And a file "download" exists with bytes:
      """
      \x89PNG\r\n\x1a\n...binary...
      """
    And a hypertext transfer protocol server is serving the workdir without content type headers
    When I ingest the hypertext transfer protocol uniform resource locator for "download" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item relpath ends with ".png"

  Scenario: Hypertext transfer protocol ingest sniffs joint photographic experts group
    Given I initialized a corpus at "corpus"
    And a file "download" exists with bytes:
      """
      \xff\xd8\xff...binary...
      """
    And a hypertext transfer protocol server is serving the workdir without content type headers
    When I ingest the hypertext transfer protocol uniform resource locator for "download" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item relpath ends with ".jpg"

  Scenario: Content sniffing keeps application octet stream when unknown
    Given I initialized a corpus at "corpus"
    And a file "download" exists with bytes:
      """
      randombytes
      """
    And a hypertext transfer protocol server is serving the workdir without content type headers
    When I ingest the hypertext transfer protocol uniform resource locator for "download" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item's sidecar includes media type "application/octet-stream"

  Scenario: Sniffed media type does not change a filename that already has an extension
    Given I initialized a corpus at "corpus"
    And a binary file "download.pdf" exists with Portable Document Format bytes
    And a hypertext transfer protocol server is serving the workdir without content type headers
    When I ingest the hypertext transfer protocol uniform resource locator for "download.pdf" into corpus "corpus"
    Then the last ingest succeeds
    And the last ingested item relpath ends with ".pdf"
