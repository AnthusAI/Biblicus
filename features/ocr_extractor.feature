Feature: RapidOCR extractor plugin
  Optical character recognition turns image bytes into derived text artifacts.

  The RapidOCR extractor provides a practical default that is pip-installable as an optional dependency.

  Scenario: RapidOCR extractor requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the RapidOCR dependency is unavailable
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I attempt to build a "ocr-rapidocr" extraction run in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[ocr]"

  Scenario: RapidOCR extractor skips non-image items
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available
    When I ingest the text "alpha" with title "Alpha" and tags "a" into corpus "corpus"
    And I build a "ocr-rapidocr" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: RapidOCR extractor produces extracted text for an image item
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text         | confidence |
      | image.png | Hello world! | 0.99       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "ocr-rapidocr" extraction run in corpus "corpus"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "Hello world!"
    And the extraction run item provenance uses extractor "ocr-rapidocr"

  Scenario: RapidOCR extractor records empty output when no text is recognized
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns empty output for filename "blank.png"
    And a file "blank.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "blank.png" into corpus "corpus"
    And I build a "ocr-rapidocr" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item is empty
    And the extraction run stats include extracted_empty_items 1

  Scenario: RapidOCR extractor ignores malformed and low-confidence entries
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns a mixed result for filename "mixed.png"
    And a file "mixed.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "mixed.png" into corpus "corpus"
    And I build a "ocr-rapidocr" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "ok"
