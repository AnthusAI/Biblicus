@integration @ocr
Feature: Optical character recognition integration
  A corpus can build a real optical character recognition extraction snapshot for image items.

  The repository does not include third-party image files. Integration tests download public sample assets at runtime.

  Scenario: RapidOCR extracts text from an image and produces empty output for a blank image
    Given a fake RapidOCR library is available that returns lines:
      | filename        | text        | confidence |
      | Hello_world.png | Hello world | 0.99       |
    And a fake RapidOCR library is available that returns empty output for filename "blank.png"
    When I download an image corpus into "corpus"
    And I build a "ocr-rapidocr" extraction snapshot in corpus "corpus"
    Then the extracted text for the item tagged "image-with-text" is not empty in the latest extraction snapshot
    And the extracted text for the item tagged "image-without-text" is empty in the latest extraction snapshot
