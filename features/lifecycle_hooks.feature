Feature: Lifecycle hooks
  The corpus lifecycle provides explicit hook points where plugins can observe and modify behavior.
  Hook inputs and outputs are validated and hook execution is recorded as structured logs.

  Scenario: After ingest hook can add a tag and is recorded
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "after_ingest" with tags "curated"
    When I ingest the text "hello" with title "Hook test" and tags "raw" into corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation includes tag "raw"
    And the shown JavaScript Object Notation includes tag "curated"
    And the corpus "corpus" hook logs include a record for hook point "after_ingest" and hook "add-tags"

  Scenario: After ingest hook does not duplicate an existing tag for a note
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "after_ingest" with tags "raw"
    When I ingest the text "hello" with title "Hook test" and tags "raw" into corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation tags equal "raw"

  Scenario: After ingest hook can add a tag for a binary item
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "after_ingest" with tags "curated"
    And a binary file "report.pdf" exists
    When I ingest the file "report.pdf" into corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation includes tag "curated"

  Scenario: After ingest hook does not duplicate an existing tag for a binary item
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "after_ingest" with tags "curated"
    And a binary file "report.pdf" exists
    When I ingest the file "report.pdf" with tags "curated" into corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation tags equal "curated"

  Scenario: Before ingest hook can add a tag
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "before_ingest" with tags "preflight"
    When I ingest the text "hello" with title "Hook test" and tags "raw" into corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation includes tag "raw"
    And the shown JavaScript Object Notation includes tag "preflight"

  Scenario: Before ingest hook does not duplicate an existing tag
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "before_ingest" with tags "raw"
    When I ingest the text "hello" with title "Hook test" and tags "raw" into corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation tags equal "raw"

  Scenario: Hook manager deduplicates repeated tags
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "before_ingest" with tags "dup,dup"
    When I ingest the text "hello" with title "Hook test" and tags " " into corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation tags equal "dup"

  Scenario: Before ingest hook can deny ingest and is recorded
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "deny-all" for hook point "before_ingest" with no tags
    When I ingest the text "hello" with title "Denied" and tags "raw" into corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Ingest denied"
    And the corpus "corpus" hook logs include a record for hook point "before_ingest" and hook "deny-all"

  Scenario: Before ingest hook can add a tag for a binary item
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "before_ingest" with tags "preflight"
    And a binary file "report.pdf" exists
    When I ingest the file "report.pdf" into corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation includes tag "preflight"

  Scenario: Before ingest hook does not duplicate an existing tag for a binary item
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "before_ingest" with tags "paper"
    And a binary file "report.pdf" exists
    When I ingest the file "report.pdf" with tags "paper" into corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation tags equal "paper"

  Scenario: Hook with no tag changes still records execution
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "after_ingest" with tags " "
    When I ingest the text "hello" with title "Hook test" and tags "raw" into corpus "corpus"
    Then the last ingest succeeds
    And the corpus "corpus" hook logs include a record for hook point "after_ingest" and hook "add-tags"

  Scenario: Hook with no tag changes runs for a binary item
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" has a configured hook "add-tags" for hook point "after_ingest" with tags " "
    And a binary file "report.pdf" exists
    When I ingest the file "report.pdf" into corpus "corpus"
    Then the last ingest succeeds
    And the corpus "corpus" hook logs include a record for hook point "after_ingest" and hook "add-tags"
