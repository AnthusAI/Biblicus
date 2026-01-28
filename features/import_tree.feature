Feature: Importing a folder tree
  A corpus should support importing an existing folder tree while preserving provenance and stable relative paths.

  Scenario: Import a folder tree into a corpus
    Given I initialized a corpus at "corpus"
    And the directory "source_tree" contains files:
      | relpath        | contents |
      | a.txt          | alpha    |
      | docs/b.md      | bravo    |
      | docs/notes.md  | ---\ntitle: Note\n---\nbody\n |
    When I import the folder tree "source_tree" into corpus "corpus" with tags "imported"
    Then the command succeeds
    And the corpus "corpus" has at least 3 items
    And the corpus "corpus" has an item with source suffix "/source_tree/a.txt"
    And the corpus "corpus" has an item with source suffix "/source_tree/docs/b.md"

  Scenario: Import can run without specifying tags
    Given I initialized a corpus at "corpus"
    And the directory "source_tree" contains files:
      | relpath | contents |
      | a.txt   | alpha    |
    When I run "import-tree source_tree" in corpus "corpus"
    Then the command succeeds
    And the corpus "corpus" has at least 1 items

  Scenario: Import respects corpus ignore patterns
    Given I initialized a corpus at "corpus"
    And the corpus "corpus" ignore file includes:
      """
      # ignore temporary files

      *.tmp
      """
    And the directory "source_tree" contains files:
      | relpath     | contents |
      | keep.md     | keep     |
      | skip.tmp    | skip     |
    When I import the folder tree "source_tree" into corpus "corpus" with tags "imported"
    Then the command succeeds
    And the corpus "corpus" has at least 1 items
    And the corpus "corpus" has no item with source suffix "/source_tree/skip.tmp"

  Scenario: Import fails when source root does not exist
    Given I initialized a corpus at "corpus"
    When I run "import-tree missing-tree --tags imported" in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "Import source root does not exist"

  Scenario: Import fails on invalid Markdown bytes
    Given I initialized a corpus at "corpus"
    And the directory "source_tree" contains a markdown file "bad.md" with invalid Unicode Transformation Format 8 bytes
    When I import the folder tree "source_tree" into corpus "corpus" with tags "imported"
    Then the command fails with exit code 2
    And standard error includes "Markdown file must be Unicode Transformation Format 8"
