@integration
Feature: Image corpus integration
  A corpus can ingest image items from remote sources and record them with correct media types.
  These items are intended for future optical character recognition extraction testing.

  Scenario: Download image samples and record tags for with-text and without-text cases
    When I download an image corpus into "corpus"
    Then the corpus contains at least 1 item with media type "image/png"
    And the corpus contains at least 1 item with media type "image/jpeg"
    And the corpus contains at least 1 item tagged "image-with-text"
    And the corpus contains at least 1 item tagged "image-without-text"
