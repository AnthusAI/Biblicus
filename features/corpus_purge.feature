Feature: Purging a corpus (dangerous operation)
  Purging deletes all items and derived files while preserving the corpus identity/config.
  It must require explicit confirmation to prevent accidents.

  Scenario: Purge requires confirmation
    Given I initialized a corpus at "corpus"
    When I run "purge" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "--confirm"

  Scenario: Purge rejects incorrect confirmation
    Given I initialized a corpus at "corpus"
    When I run "purge --confirm wrong" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Confirmation mismatch"

  Scenario: Purge deletes all items and resets catalog
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "A" and tags "t" into corpus "corpus"
    And I run "purge --confirm corpus" in corpus "corpus"
    Then the command succeeds
    And the corpus "corpus" raw folder is empty
    And the corpus "corpus" catalog has 0 items

  Scenario: Purge removes extra derived files and recreates raw folder
    Given I initialized a corpus at "corpus"
    And I create an extra derived folder in corpus "corpus"
    And I delete the corpus "corpus" raw folder
    When I run "purge --confirm corpus" in corpus "corpus"
    Then the command succeeds
    And the corpus "corpus" raw folder is empty
