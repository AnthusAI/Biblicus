@integration
Feature: Mixed modality extraction integration
  A mixed corpus can be extracted using multiple extractor plugins, including cases where extraction yields empty text.

  Scenario: Portable Document Format extraction produces text when available and records empty output when unavailable
    When I download a mixed corpus into "corpus"
    And I build a "pdf-text" extraction snapshot in corpus "corpus"
    Then the extracted text for the item tagged "pdf-sample" is not empty in the latest extraction snapshot
    And the extracted text for the item tagged "scanned" is empty in the latest extraction snapshot

  Scenario: Pass-through text extractor ignores binary items
    When I download a mixed corpus into "corpus"
    And I build a "pass-through-text" extraction snapshot in corpus "corpus"
    Then the extracted text for the item tagged "html" is not empty in the latest extraction snapshot
    And the extraction snapshot does not include extracted text for the item tagged "image"
