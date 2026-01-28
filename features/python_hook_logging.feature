Feature: Hook logging redaction
  Hook logs must avoid storing credentials embedded in source uniform resource identifiers.

  Scenario: Hook log redacts user info in source uniform resource identifier
    Given I have an initialized corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "after_ingest" with tags "x"
    When I ingest an item via the Python application programming interface into corpus "corpus" with source uniform resource identifier "http://user:pass@example.com/private" and filename "note.txt"
    Then the corpus "corpus" hook logs do not include "user:pass@"
    And the corpus "corpus" hook logs include "example.com"

