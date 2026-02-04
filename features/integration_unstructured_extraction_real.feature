@integration @unstructured
Feature: Unstructured extraction integration (real)
  Unstructured should extract text from non-text items in a mixed corpus using real dependencies.

  Scenario: Unstructured extracts text from DOCX and handles scanned Portable Document Format
    Given Poppler is available for Portable Document Format parsing
    When I download a mixed corpus into "corpus"
    And I build a "unstructured" extraction snapshot in corpus "corpus"
    Then the extracted text for the item tagged "docx-sample" is not empty in the latest extraction snapshot
    And the extracted text for the item tagged "scanned" is empty in the latest extraction snapshot
