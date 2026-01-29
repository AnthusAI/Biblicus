@integration @ocr
Feature: Optical character recognition integration
  A corpus can build a real optical character recognition extraction run for image items.

  The repository does not include third-party image files. Integration tests download public sample assets at runtime.

  Scenario: RapidOCR extracts text from an image and produces empty output for a blank image
    When I download an image corpus into "corpus"
    And I build a "ocr-rapidocr" extraction run in corpus "corpus"
    Then the extracted text for the item tagged "image-with-text" is not empty in the latest extraction run
    And the extracted text for the item tagged "image-without-text" is empty in the latest extraction run
