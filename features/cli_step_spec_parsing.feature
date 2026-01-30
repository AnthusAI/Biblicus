Feature: Command-line step spec parsing with JSON values
  Step specs support JSON-encoded values for nested configuration objects.

  Scenario: Parse step spec with JSON-encoded nested dict value
    Given I initialized a corpus at "corpus"
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text | confidence |
      | image.png | JSON | 0.85       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build an extraction run in corpus "corpus" using extractor "ocr-paddleocr-vl" with step spec "ocr-paddleocr-vl:backend={\"mode\":\"local\"},min_confidence=0.5"
    Then the extracted text for the last ingested item equals "JSON"

  Scenario: Parse step spec with multiple config values including JSON
    Given I initialized a corpus at "corpus"
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text | confidence |
      | image.png | Test | 0.95       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build an extraction run in corpus "corpus" using extractor "ocr-paddleocr-vl" with step spec "ocr-paddleocr-vl:joiner=\\n,backend={\"mode\":\"local\"},use_angle_cls=true"
    Then the extraction run includes extracted text for the last ingested item

  Scenario: Parse step spec with quoted string value
    Given I initialized a corpus at "corpus"
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text         | confidence |
      | image.png | Quoted value | 0.90       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build an extraction run in corpus "corpus" using extractor "ocr-paddleocr-vl" with step spec "ocr-paddleocr-vl:joiner=\", \",backend={\"mode\":\"local\"}"
    Then the extraction run includes extracted text for the last ingested item
