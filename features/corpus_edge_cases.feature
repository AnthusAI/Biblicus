Feature: Corpus edge cases and robustness
  The corpus is mutable, user-editable, and should behave predictably across edge cases.

  Scenario: Init fails when a corpus already exists
    Given I initialized a corpus at "corpus"
    When I attempt to initialize a corpus at "corpus"
    Then the command fails with exit code 2
    And standard error includes "Corpus already exists"

  Scenario: Running commands outside a corpus fails
    When I run "list" without specifying a corpus
    Then the command fails with exit code 2
    And standard error includes "Not a Biblicus corpus"

  Scenario: Ingest text without title or tags
    Given I initialized a corpus at "corpus"
    When I ingest the text "hi" with no metadata into corpus "corpus"
    Then the last ingest succeeds
    When I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation has no tags
    And the shown JavaScript Object Notation has no title

  Scenario: Sidecar metadata must be a mapping
    Given I initialized a corpus at "corpus"
    And a binary file "blob.bin" exists
    When I ingest the file "blob.bin" with tags "t" into corpus "corpus"
    And I overwrite the last ingested item's sidecar with a Yet Another Markup Language list
    When I run "reindex" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Sidecar metadata must be a mapping"

  Scenario: Reindex rejects markdown files that are not Unicode Transformation Format 8
    Given I initialized a corpus at "corpus"
    And a raw file with universally unique identifier "00000000-0000-0000-0000-000000000003" exists in corpus "corpus" named "bad.md" with invalid Unicode Transformation Format 8 bytes
    When I run "reindex" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Markdown file must be Unicode Transformation Format 8"

  Scenario: Reindex ignores invalid biblicus.id and falls back to universally unique identifier prefix
    Given I initialized a corpus at "corpus"
    And a raw file with universally unique identifier "00000000-0000-0000-0000-000000000002" exists in corpus "corpus" named "id-bad.md" with contents "x"
    And a sidecar for raw file "00000000-0000-0000-0000-000000000002--id-bad.md" exists in corpus "corpus" with Yet Another Markup Language:
      """
      biblicus:
        id: not-a-universally-unique-identifier
      """
    When I reindex corpus "corpus"
    Then reindex stats include inserted 1
    And reindex stats include skipped 0

  Scenario: Reindex ignores non-string biblicus.id and falls back to universally unique identifier prefix
    Given I initialized a corpus at "corpus"
    And a raw file with universally unique identifier "00000000-0000-0000-0000-000000000004" exists in corpus "corpus" named "id-int.md" with contents "x"
    And a sidecar for raw file "00000000-0000-0000-0000-000000000004--id-int.md" exists in corpus "corpus" with Yet Another Markup Language:
      """
      biblicus:
        id: 123
      """
    When I reindex corpus "corpus"
    Then reindex stats include inserted 1
    And reindex stats include skipped 0

  Scenario: Reindex skips files with non-universally unique identifier prefixes
    Given I initialized a corpus at "corpus"
    And a raw file named "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx--oops.txt" exists in corpus "corpus" with contents "y"
    When I reindex corpus "corpus"
    Then reindex stats include skipped 1

  Scenario: Reindex skips files without a universally unique identifier prefix
    Given I initialized a corpus at "corpus"
    And a raw file named "short.txt" exists in corpus "corpus" with contents "x"
    When I reindex corpus "corpus"
    Then reindex stats include skipped 1

  Scenario: Listing works even if catalog order is missing
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "T" and tags "t" into corpus "corpus"
    And I clear the corpus catalog order list in corpus "corpus"
    And I list items in corpus "corpus"
    Then the list output includes the last ingested item identifier

  Scenario: Listing skips unknown identifiers in catalog order
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "T" and tags "t" into corpus "corpus"
    And I prepend an unknown identifier to the corpus catalog order list in corpus "corpus"
    And I list items in corpus "corpus"
    Then the list output includes the last ingested item identifier

  Scenario: Reindex respects media_type from sidecar
    Given I initialized a corpus at "corpus"
    And a binary file "data.bin" exists
    When I ingest the file "data.bin" with tags "raw" into corpus "corpus"
    And I set the last ingested item's sidecar media type to "application/pdf"
    And I reindex corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation includes media type "application/pdf"

  Scenario: Reindex merges biblicus provenance from front matter and sidecar
    Given I initialized a corpus at "corpus"
    When I ingest the text "hello" with title "T" and tags "t" into corpus "corpus"
    And I write a sidecar for the last ingested item with Yet Another Markup Language:
      """
      biblicus:
        source: sidecar
      """
    And I reindex corpus "corpus"
    And I show the last ingested item in corpus "corpus"
    Then the shown JavaScript Object Notation includes source uniform resource identifier "sidecar"

  Scenario: Reindex works when no biblicus metadata exists
    Given I initialized a corpus at "corpus"
    And a raw file with universally unique identifier "00000000-0000-0000-0000-000000000005" exists in corpus "corpus" named "plain.md" with contents "hello"
    When I reindex corpus "corpus"
    Then reindex stats include inserted 1
    And reindex stats include skipped 0

  Scenario: Reindex ignores invalid sidecar biblicus type
    Given I initialized a corpus at "corpus"
    And a raw file with universally unique identifier "00000000-0000-0000-0000-000000000006" exists in corpus "corpus" named "mix.md" with contents:
      """
      ---
      biblicus:
        source: front
      ---
      body
      """
    And a sidecar for raw file "00000000-0000-0000-0000-000000000006--mix.md" exists in corpus "corpus" with Yet Another Markup Language:
      """
      biblicus: nope
      """
    When I reindex corpus "corpus"
    When I show item "00000000-0000-0000-0000-000000000006" in corpus "corpus"
    Then the shown JavaScript Object Notation includes source uniform resource identifier "front"
