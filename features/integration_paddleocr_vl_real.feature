@integration @ocr @paddleocr
Feature: PaddleOCR-VL integration (real)
  A corpus can build a real PaddleOCR-VL extraction snapshot for image items.

  Scenario: PaddleOCR-VL extracts text from an image and produces empty output for a blank image
    When I download an image corpus into "corpus"
    And I build a "ocr-paddleocr-vl" extraction snapshot in corpus "corpus" with config:
      | key            | value |
      | min_confidence | 0.0   |
    Then the extracted text for the item tagged "image-with-text" is not empty in the latest extraction snapshot
    And the extracted text for the item tagged "image-without-text" is empty in the latest extraction snapshot
