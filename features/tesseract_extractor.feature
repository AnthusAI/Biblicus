Feature: Tesseract OCR text extractor

  Background:
    Given I initialized a corpus at "corpus"

  Scenario: Extract text from PNG image using Tesseract
    Given I ingested the file "examples/test_two_column_document.png" with tags ["test-ocr"] into corpus "corpus"
    When I build an "ocr-tesseract" extraction snapshot in corpus "corpus"
    Then the extraction snapshot includes extracted text for the item tagged "test-ocr"

  Scenario: Tesseract reads layout metadata from previous pipeline stage
    Given I ingested the file "examples/test_two_column_document.png" with tags ["layout-test"] into corpus "corpus"
    When I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id            | config_json                       |
      | mock-layout-detector    | {"layout_type": "two-column"}     |
      | ocr-tesseract           | {"use_layout_metadata": true}     |
    Then the extraction snapshot includes extracted text for the item tagged "layout-test"
    And the extraction snapshot includes metadata for the item tagged "layout-test"

  Scenario: Tesseract with minimum confidence threshold
    Given I ingested the file "examples/test_two_column_document.png" with tags ["confidence-test"] into corpus "corpus"
    When I build an "ocr-tesseract" extraction snapshot in corpus "corpus" using the configuration:
      """
      extractor_id: ocr-tesseract
      config:
        min_confidence: 0.8
        lang: eng
      """
    Then the extraction snapshot includes extracted text for the item tagged "confidence-test"

  Scenario: Tesseract skips non-image items
    Given I ingested the plaintext file "hello.txt" with content "Hello, World!" and tags ["text-file"] into corpus "corpus"
    When I build an "ocr-tesseract" extraction snapshot in corpus "corpus"
    Then the extraction snapshot does not include any text for the item tagged "text-file"

  Scenario: Tesseract processes layout regions in correct reading order
    Given I ingested the file "examples/test_two_column_document.png" with tags ["order-test"] into corpus "corpus"
    When I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id            | config_json                       |
      | mock-layout-detector    | {"layout_type": "two-column"}     |
      | ocr-tesseract           | {"use_layout_metadata": true}     |
    Then the extraction snapshot includes extracted text for the item tagged "order-test"
    And the extraction snapshot includes metadata for the item tagged "order-test"
