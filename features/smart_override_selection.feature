Feature: Smart override selection extractor
  The smart override selector intelligently chooses between extraction results based on
  content quality and confidence scores.

  Scenario: Smart override keeps last extraction when it has meaningful content
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text       | confidence |
      | image.png | Legacy OCR | 0.80       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text     | confidence |
      | image.png | Good OCR | 0.95       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_text_length: 5
      """
    Then the extracted text for the last ingested item equals "Good OCR"
    And the extraction run item provenance uses extractor "ocr-paddleocr-vl"

  Scenario: Smart override falls back to previous when last has low confidence
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text       | confidence |
      | image.png | Legacy OCR | 0.85       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text    | confidence |
      | image.png | Bad OCR | 0.10       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_confidence_threshold: 0.7
      """
    Then the extracted text for the last ingested item equals "Legacy OCR"
    And the extraction run item provenance uses extractor "ocr-rapidocr"

  Scenario: Smart override uses last extraction for non-matching media types
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha" with title "Alpha" and tags "a" into corpus "corpus"
    And I ingest the text "beta" with title "Beta" and tags "b" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: metadata-text
            config: {}
          - extractor_id: pass-through-text
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
      """
    Then the extraction run includes extracted text for all items

  Scenario: Smart override requires minimum text length
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text               | confidence |
      | image.png | Longer text result | 0.75       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text | confidence |
      | image.png | xy   | 0.95       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_text_length: 10
      """
    Then the extracted text for the last ingested item equals "Longer text result"
    And the extraction run item provenance uses extractor "ocr-rapidocr"

  Scenario: Smart override handles empty text in last extraction
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text          | confidence |
      | image.png | Fallback text | 0.85       |
    And a fake PaddleOCR library is available that returns empty output for filename "image.png"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_confidence_threshold: 0.7
      """
    Then the extracted text for the last ingested item equals "Fallback text"
    And the extraction run item provenance uses extractor "ocr-rapidocr"

  Scenario: Smart override handles extraction with no confidence score
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text          | confidence |
      | image.png | No confidence | 0.50       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text        | confidence |
      | image.png | Good result | 0.90       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_confidence_threshold: 0.7
      """
    Then the extracted text for the last ingested item equals "Good result"
    And the extraction run item provenance uses extractor "ocr-paddleocr-vl"

  Scenario: Smart override prefers previous extraction when last has short text and previous has high confidence
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text                          | confidence |
      | image.png | High confidence previous text | 0.92       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text | confidence |
      | image.png | abc  | 0.55       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_confidence_threshold: 0.75
              min_text_length: 10
      """
    Then the extracted text for the last ingested item equals "High confidence previous text"
    And the extraction run item provenance uses extractor "ocr-rapidocr"

  Scenario: Smart override returns None when no candidates have text
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha" with title "Alpha" and tags "a" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "text/*"
      """
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: Smart override falls back to last when all previous have low confidence
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text     | confidence |
      | image.png | Low conf | 0.30       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text | confidence |
      | image.png | Last | 0.40       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config:
              min_confidence: 0.0
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_confidence_threshold: 0.7
              min_text_length: 5
      """
    Then the extracted text for the last ingested item equals "Last"
    And the extraction run item provenance uses extractor "ocr-paddleocr-vl"

  Scenario: Smart override skips previous extraction with good length but low confidence
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text                      | confidence |
      | image.png | Good length but low conf  | 0.40       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text                   | confidence |
      | image.png | Final extraction works | 0.85       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_confidence_threshold: 0.7
              min_text_length: 10
      """
    Then the extracted text for the last ingested item equals "Final extraction works"
    And the extraction run item provenance uses extractor "ocr-paddleocr-vl"

  Scenario: Smart override rejects last extraction with good length but low confidence
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text                   | confidence |
      | image.png | Previous good text     | 0.85       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text              | confidence |
      | image.png | Last low conf     | 0.60       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_confidence_threshold: 0.7
              min_text_length: 5
      """
    Then the extracted text for the last ingested item equals "Previous good text"
    And the extraction run item provenance uses extractor "ocr-rapidocr"

  Scenario: Smart override skips multiple previous with good length but low confidence
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text                        | confidence |
      | image.png | First extraction high conf  | 0.90       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text                    | confidence |
      | image.png | Middle good length low  | 0.40       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: metadata-text
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_confidence_threshold: 0.7
              min_text_length: 10
      """
    Then the extracted text for the last ingested item equals "First extraction high conf"
    And the extraction run item provenance uses extractor "ocr-rapidocr"

  Scenario: Smart override loops through multiple previous extractions with low confidence
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text                     | confidence |
      | image.png | First high confidence    | 0.90       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text                      | confidence |
      | image.png | Second low confidence ok  | 0.50       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-rapidocr
            config: {}
          - extractor_id: pass-through-text
            config: {}
          - extractor_id: ocr-paddleocr-vl
            config: {}
          - extractor_id: pass-through-text
            config: {}
          - extractor_id: select-smart-override
            config:
              media_type_patterns:
                - "image/*"
              min_confidence_threshold: 0.7
              min_text_length: 10
      """
    Then the extracted text for the last ingested item equals "First high confidence"
    And the extraction run item provenance uses extractor "ocr-rapidocr"

  Scenario: Smart override handles malformed JSON in config gracefully
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text | confidence |
      | image.png | Text | 0.90       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I attempt to build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id             | config_json                              |
      | ocr-rapidocr             | {}                                       |
      | select-smart-override    | {"media_type_patterns":"[bad json"}     |
    Then the command fails with exit code 2
