@integration @ocr @paddleocr
Feature: PaddleOCR layout integration (real)
  A corpus can build a real PaddleOCR layout extraction snapshot for image items.

  Scenario: PaddleOCR layout metadata is produced for an image
    When I download an image corpus into "corpus"
    And I build a "paddleocr-layout" extraction snapshot in corpus "corpus"
    Then the extraction snapshot includes metadata for the item tagged "image-with-text"
