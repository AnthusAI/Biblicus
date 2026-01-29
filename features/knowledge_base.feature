Feature: Knowledge base (turnkey workflow)
  A knowledge base is a high-level workflow that hides the plumbing while keeping behavior explicit.
  It should accept a folder, ingest files, build defaults, and allow retrieval with minimal configuration.

  Scenario: Build a knowledge base from a folder and query it
    Given a folder "notes" exists with text files:
      | filename | contents                                                   |
      | note1.txt | The user's name is Tactus Maximus.                       |
      | note2.txt | Primary button style preference: the user's favorite color is magenta. |
    When I create a knowledge base from folder "notes" only
    And I query the knowledge base for "Primary button style preference"
    Then the knowledge base returns evidence that includes "favorite color is magenta"

  Scenario: Knowledge base context pack is shaped with a token budget
    Given a folder "notes" exists with text files:
      | filename | contents                              |
      | note1.txt | one two three                         |
      | note2.txt | four five six                         |
    When I create a knowledge base from folder "notes" only
    And I query the knowledge base for "one"
    And I build a context pack from the knowledge base query with token budget 3
    Then the context pack text equals:
      """
      one two three
      """

  Scenario: Knowledge base context pack defaults to no token budget
    Given a folder "notes" exists with text files:
      | filename | contents      |
      | note1.txt | alpha beta   |
    When I create a knowledge base from folder "notes" only
    And I query the knowledge base for "alpha"
    And I build a context pack from the knowledge base query without a token budget
    Then the context pack text equals:
      """
      alpha beta
      """

  Scenario: Knowledge base rejects missing folder
    When I attempt to create a knowledge base from folder "missing"
    Then the knowledge base error includes "does not exist"

  Scenario: Knowledge base rejects non-folder path
    Given a file "not-a-folder.txt" exists with contents "hello"
    When I attempt to create a knowledge base from folder "not-a-folder.txt"
    Then the knowledge base error includes "not a directory"

  Scenario: Knowledge base can use an explicit corpus root
    Given a folder "notes" exists with text files:
      | filename | contents |
      | note1.txt | alpha |
    And a folder "kb-root" exists
    When I create a knowledge base from folder "notes" using corpus root "kb-root"
    And I query the knowledge base for "alpha"
    Then the knowledge base returns evidence that includes "alpha"
