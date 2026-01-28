Feature: Source loading helper
  The source loading helper supports file paths, file uniform resource identifiers, and hypertext transfer protocol addresses.

  Scenario: Loading a string path returns bytes and a file source uniform resource identifier
    Given I have a file "hello.txt" with contents "hello"
    When I load the source "hello.txt"
    Then the source payload filename is "hello.txt"
    And the source payload source uniform resource identifier starts with "file://"

