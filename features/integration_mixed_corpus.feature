@integration
Feature: Mixed modality integration corpus
  The integration corpus downloads public files into a local corpus and adds a small generated sample.

  The repository does not include downloaded content.

  Scenario: Download and ingest a mixed corpus
    When I download a mixed corpus into "corpus"
    Then the corpus contains at least 5 items
    And the corpus contains at least 1 item with media type "text/markdown"
    And the corpus contains at least 1 item with media type "text/html"
    And the corpus contains at least 1 item with media type "image/jpeg"
    And the corpus contains at least 1 item with media type "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    And the corpus contains at least 2 items with media type "application/pdf"
    And the corpus contains at least 1 item tagged "scanned"
