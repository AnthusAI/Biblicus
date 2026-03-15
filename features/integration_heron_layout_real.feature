@integration @layout @heron
Feature: Heron layout integration (real)
  A corpus can build a real Heron layout extraction snapshot for image items.

  Scenario: Heron layout metadata is produced for an image
    When I download an image corpus into "corpus"
    And I build a "heron-layout" extraction snapshot in corpus "corpus"
    Then the extraction snapshot includes metadata for the item tagged "image-with-text"
