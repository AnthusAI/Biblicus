Feature: Collection partitions
  A collection can tag subfolders as table partitions within a single corpus.

  Scenario: Partitioned tables tag items with table name
    Given a collection "tables" is configured to partition subfolders as tables
    And the collection has remote subfolders:
      | name  |
      | users |
      | orders |
    And the remote folder "users" contains objects:
      | key            | content |
      | users/1.json   | {"id":1} |
    And the remote folder "orders" contains objects:
      | key             | content |
      | orders/9.json   | {"id":9} |
    When I pull the collection "tables"
    Then the corpus "corpora/tables" has an item tagged with table "users"
    And the corpus "corpora/tables" has an item tagged with table "orders"
