Feature: Corpus identity and discovery
  Corpora can be referenced by a filesystem path or a file:// uniform resource identifier, and can be discovered
  by searching upward from the current working directory.

  Scenario: Use file:// uniform resource identifier to reference a corpus
    Given I initialized a corpus at "corpus"
    When I list items in the corpus by file uniform resource identifier for "corpus"
    Then the command succeeds

  Scenario: Find a corpus by searching upward from the current working directory
    Given I initialized a corpus at "corpus"
    And I create the directory "corpus/subdir"
    When I list items from within "corpus/subdir"
    Then the command succeeds
