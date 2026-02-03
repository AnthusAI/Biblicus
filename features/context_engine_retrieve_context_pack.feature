Feature: Context engine retrieval helper
  The context engine should provide a helper that converts retrieval results into context packs.

  Scenario: Retrieve a context pack from a corpus with the context engine helper
    Given I have an initialized corpus at "corpus"
    And I ingest text items into corpus "corpus":
      | filename | contents          |
      | cats.txt | Cats love naps.   |
      | dogs.txt | Dogs love walks.  |
    When I retrieve a context pack from corpus "corpus" with retriever "embedding-index-inmemory" for query "cats"
    Then the context pack text contains "Cats"

  Scenario: Missing configuration configuration errors clearly
    Given I have an initialized corpus at "corpus"
    And I ingest text items into corpus "corpus":
      | filename | contents          |
      | cats.txt | Cats love naps.   |
    When I retrieve a context pack from corpus "corpus" with retriever "embedding-index-inmemory" for query "cats" without a configuration config
    Then the context pack error should mention "No retrieval snapshot available"

  Scenario: Existing retrieval snapshot is reused without configuration config
    Given I have an initialized corpus at "corpus"
    And I ingest text items into corpus "corpus":
      | filename | contents          |
      | cats.txt | Cats love naps.   |
      | dogs.txt | Dogs love walks.  |
    When I retrieve a context pack from corpus "corpus" with retriever "embedding-index-inmemory" for query "cats"
    And I retrieve a context pack from corpus "corpus" with retriever "embedding-index-inmemory" for query "cats" without a configuration config
    Then the context pack text matches the previous result

  Scenario: Retrieval snapshot id overrides configuration config
    Given I have an initialized corpus at "corpus"
    And I ingest text items into corpus "corpus":
      | filename | contents        |
      | cats.txt | Cats love naps. |
    When I retrieve a context pack from corpus "corpus" with retriever "embedding-index-inmemory" for query "cats" and store the snapshot id
    And I retrieve a context pack from corpus "corpus" with retriever "embedding-index-inmemory" for query "cats" using snapshot id with max tokens 5
    Then the context pack text contains "Cats"
