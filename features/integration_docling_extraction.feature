@integration @docling
Feature: Docling extraction integration
  Docling extractors should run against a real Portable Document Format corpus.

  Scenario: Docling Granite extracts text from a Portable Document Format corpus
    When I download a Portable Document Format corpus into "corpus"
    And I build a "docling-granite" extraction snapshot in corpus "corpus"
    Then the extracted text for the item tagged "pdf" is not empty in the latest extraction snapshot

  Scenario: Docling Smol extracts text from a Portable Document Format corpus
    When I download a Portable Document Format corpus into "corpus"
    And I build a "docling-smol" extraction snapshot in corpus "corpus"
    Then the extracted text for the item tagged "pdf" is not empty in the latest extraction snapshot
