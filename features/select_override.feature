Feature: Simple override selection extractor
  The simple override selector provides basic override behavior for matching media types.

  Scenario: Simple override uses last extraction for matching media types
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns lines:
      | filename  | text        | confidence |
      | image.png | First OCR   | 0.80       |
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text        | confidence |
      | image.png | Second OCR  | 0.85       |
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
          - extractor_id: select-override
            config:
              media_type_patterns:
                - "image/*"
      """
    Then the extracted text for the last ingested item equals "Second OCR"
    And the extraction run item provenance uses extractor "ocr-paddleocr-vl"

  Scenario: Simple override uses last extraction for non-matching media types
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
          - extractor_id: select-override
            config:
              media_type_patterns:
                - "image/*"
      """
    Then the extraction run includes extracted text for all items

  Scenario: Simple override falls back to first extraction when enabled
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
          - extractor_id: select-override
            config:
              media_type_patterns:
                - "image/*"
              fallback_to_first: true
      """
    Then the extraction run includes extracted text for all items

  Scenario: Simple override returns nothing when no prior extractions exist
    Given I initialized a corpus at "corpus"
    And a fake RapidOCR library is available that returns empty output for filename "image.png"
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
          - extractor_id: select-override
            config:
              media_type_patterns:
                - "image/*"
      """
    Then the extracted text for the last ingested item is empty

  Scenario: Simple override returns None when no candidates have text
    Given I initialized a corpus at "corpus"
    When I ingest the text "alpha" with title "Alpha" and tags "a" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: select-override
            config:
              media_type_patterns:
                - "text/*"
      """
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: Simple override handles malformed JSON in config gracefully
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
      | extractor_id      | config_json                              |
      | ocr-rapidocr      | {}                                       |
      | select-override   | {"media_type_patterns":"[bad json"}     |
    Then the command fails with exit code 2
