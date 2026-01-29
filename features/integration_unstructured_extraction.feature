@integration @unstructured
Feature: Unstructured extraction integration
  The Unstructured extractor is intended as a catchall text extractor for non-text items.

  This feature validates that Unstructured can extract usable text from at least one
  non-text format in the mixed integration corpus.

  Scenario: Unstructured extracts text from a document and does not crash on other non-text items
    When I download a mixed corpus into "corpus"
    And I build a "unstructured" extraction run in corpus "corpus"
    Then the extracted text for the item tagged "docx-sample" is not empty in the latest extraction run
