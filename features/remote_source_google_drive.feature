Feature: Remote Google Drive corpus source
  A remote Google Drive folder source mirrors files into the corpus.

  Scenario: Pull downloads nested files from Google Drive
    Given I initialized a corpus at "corpus"
    And a remote Google Drive source is configured for corpus "corpus" with folder url "https://drive.google.com/drive/folders/folder123?usp=drive_link" and no prefix
    And a fake Google Drive source contains files:
      | path               | content      |
      | docs/a.md          | Alpha note   |
      | docs/nested/b.txt  | Beta note    |
    When I pull the remote source for corpus "corpus"
    Then the catalog contains source uris:
      | gdrive://folder123/docs/a.md |
      | gdrive://folder123/docs/nested/b.txt |

  Scenario: Pull applies prefix filtering for Google Drive
    Given I initialized a corpus at "corpus"
    And a remote Google Drive source is configured for corpus "corpus" with folder url "https://drive.google.com/drive/folders/folder123?usp=drive_link" and prefix "docs/nested/"
    And a fake Google Drive source contains files:
      | path               | content      |
      | docs/a.md          | Alpha note   |
      | docs/nested/b.txt  | Beta note    |
    When I pull the remote source for corpus "corpus"
    Then the catalog contains source uris:
      | gdrive://folder123/docs/nested/b.txt |
    And the catalog does not contain source uri "gdrive://folder123/docs/a.md"

  Scenario: Missing gdown dependency errors on pull
    Given I initialized a corpus at "corpus"
    And the gdown dependency is unavailable
    And a remote Google Drive source is configured for corpus "corpus" with folder url "https://drive.google.com/drive/folders/folder123?usp=drive_link" and no prefix
    When I pull the remote source for corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "gdown"
