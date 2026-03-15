@integration @ocr
Feature: Optical character recognition integration (real)
  A corpus can build a real optical character recognition extraction snapshot for image items.

  Scenario: RapidOCR extracts text from an image and produces empty output for a blank image
    When I download an image corpus into "corpus"
    And I build a "ocr-rapidocr" extraction snapshot in corpus "corpus"
    Then the extracted text for the item tagged "image-with-text" is not empty in the latest extraction snapshot
    And the extracted text for the item tagged "image-without-text" is empty in the latest extraction snapshot
