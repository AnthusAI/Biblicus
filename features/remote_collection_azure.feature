Feature: Remote collection (Azure Blob)
  A collection mirrors a remote root and materializes corpora per subfolder.

  Scenario: Collection pull discovers subfolders and creates corpora
    Given a collection "nexus" is configured for Azure Blob container "nexus"
    And the collection has remote subfolders:
      | name     |
      | catalyst |
      | acme     |
    When I pull the collection "nexus"
    Then a corpus exists at "corpora/nexus/catalyst"
    And a corpus exists at "corpora/nexus/acme"

  Scenario: Collection pull mirrors content for each corpus
    Given a collection "nexus" is configured for Azure Blob container "nexus"
    And the collection has remote subfolders:
      | name |
      | catalyst |
    And the remote folder "catalyst" contains objects:
      | key              | content |
      | catalyst/a.txt   | Alpha   |
    When I pull the collection "nexus"
    Then the corpus "corpora/nexus/catalyst" contains a mirrored item for "catalyst/a.txt"

  Scenario: Collection pull archives missing remote folders
    Given a collection "nexus" is configured for Azure Blob container "nexus"
    And a corpus exists at "corpora/nexus/legacy"
    And the collection has remote subfolders:
      | name |
      | catalyst |
    When I pull the collection "nexus"
    Then the corpus "corpora/nexus/legacy" is archived
