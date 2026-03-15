Feature: Source loading helper
  The source loading helper supports file paths, file uniform resource identifiers, and hypertext transfer protocol addresses.

  Scenario: Loading a string path returns bytes and a file source uniform resource identifier
    Given I have a file "hello.txt" with contents "hello"
    When I load the source "hello.txt"
    Then the source payload filename is "hello.txt"
    And the source payload source uniform resource identifier starts with "file://"

  Scenario: Loading a binary file infers media type and extension
    Given I have a binary file "mystery" with bytes:
      """
      255044462d312e340a
      """
    When I load the source "mystery"
    Then the source payload filename is "mystery.pdf"
    And the source payload media type is "application/pdf"

  Scenario: Loading a file uniform resource identifier for a directory uses index
    Given I have a file "site/index.html" with contents "<html>ok</html>"
    When I load the source uniform resource identifier for "site"
    Then the source payload filename is "index.html"
    And the source payload media type is "text/html"

  Scenario: Loading a file uniform resource identifier for a directory without index fails
    Given I have a directory "empty"
    When I attempt to load the source uniform resource identifier for "empty"
    Then the source load error includes "Directory source lacks index"
