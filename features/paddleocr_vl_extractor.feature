Feature: PaddleOCR-VL extractor plugin
  Optical character recognition using PaddleOCR-VL vision-language model.

  The PaddleOCR-VL extractor provides advanced OCR capabilities with improved accuracy
  for complex layouts and multilingual text. It supports both local and API inference modes.

  @integration
  Scenario: PaddleOCR-VL extractor requires an optional dependency for local mode
    Given I initialized a corpus at "corpus"
    And the PaddleOCR dependency is unavailable
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I attempt to build a "ocr-paddleocr-vl" extraction run in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[paddleocr]"

  Scenario: PaddleOCR-VL extractor skips non-image items
    Given I initialized a corpus at "corpus"
    And a fake PaddleOCR library is available
    When I ingest the text "alpha" with title "Alpha" and tags "a" into corpus "corpus"
    And I build a "ocr-paddleocr-vl" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: PaddleOCR-VL extractor produces extracted text for an image item
    Given I initialized a corpus at "corpus"
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text         | confidence |
      | image.png | Hello world! | 0.99       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "ocr-paddleocr-vl" extraction run in corpus "corpus"
    Then the extraction run includes extracted text for the last ingested item
    And the extracted text for the last ingested item equals "Hello world!"
    And the extraction run item provenance uses extractor "ocr-paddleocr-vl"

  Scenario: PaddleOCR-VL extractor records empty output when no text is recognized
    Given I initialized a corpus at "corpus"
    And a fake PaddleOCR library is available that returns empty output for filename "blank.png"
    And a file "blank.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "blank.png" into corpus "corpus"
    And I build a "ocr-paddleocr-vl" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item is empty
    And the extraction run stats include extracted_empty_items 1

  Scenario: PaddleOCR-VL extractor filters lines by minimum confidence threshold
    Given I initialized a corpus at "corpus"
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text       | confidence |
      | test.png  | High conf  | 0.95       |
      | test.png  | Low conf   | 0.30       |
    And a file "test.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "test.png" into corpus "corpus"
    And I build a "ocr-paddleocr-vl" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "High conf"

  Scenario: PaddleOCR-VL extractor API mode requires api_provider
    Given I initialized a corpus at "corpus"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I attempt to build a "ocr-paddleocr-vl" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: ocr-paddleocr-vl
      config:
        backend:
          mode: api
      """
    Then the command fails with exit code 2

  Scenario: PaddleOCR-VL extractor works in API mode with HuggingFace using environment variable API key
    Given I initialized a corpus at "corpus"
    And the environment variable "HUGGINGFACE_API_KEY" is set to "test-api-key"
    And a fake requests library returns HuggingFace OCR response for model "PaddlePaddle/PaddleOCR-VL" with text "API extracted text"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build an extraction run in corpus "corpus" using extractor "ocr-paddleocr-vl" with step spec "ocr-paddleocr-vl:backend={\"mode\":\"api\",\"api_provider\":\"huggingface\",\"model_id\":\"PaddlePaddle/PaddleOCR-VL\"}"
    Then the extracted text for the last ingested item equals "API extracted text"
    And the extraction run item provenance uses extractor "ocr-paddleocr-vl"

  Scenario: PaddleOCR-VL extractor parses API string response format
    Given I initialized a corpus at "corpus"
    And the environment variable "HUGGINGFACE_API_KEY" is set to "test-api-key"
    And a fake requests library returns HuggingFace string response for model "PaddlePaddle/PaddleOCR-VL" with value "Simple string response"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build an extraction run in corpus "corpus" using extractor "ocr-paddleocr-vl" with step spec "ocr-paddleocr-vl:backend={\"mode\":\"api\",\"api_provider\":\"huggingface\",\"model_id\":\"PaddlePaddle/PaddleOCR-VL\"}"
    Then the extracted text for the last ingested item equals "Simple string response"

  Scenario: PaddleOCR-VL extractor parses API list response format
    Given I initialized a corpus at "corpus"
    And the environment variable "HUGGINGFACE_API_KEY" is set to "test-api-key"
    And a fake requests library returns HuggingFace list response for model "PaddlePaddle/PaddleOCR-VL" with text "List format response"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build an extraction run in corpus "corpus" using extractor "ocr-paddleocr-vl" with step spec "ocr-paddleocr-vl:backend={\"mode\":\"api\",\"api_provider\":\"huggingface\",\"model_id\":\"PaddlePaddle/PaddleOCR-VL\"}"
    Then the extracted text for the last ingested item equals "List format response"


  Scenario: PaddleOCR-VL extractor handles malformed JSON in config gracefully
    Given I initialized a corpus at "corpus"
    And a fake PaddleOCR library is available that returns lines:
      | filename  | text    | confidence |
      | image.png | Works   | 0.90       |
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I attempt to build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id     | config_json          |
      | ocr-paddleocr-vl | {"backend":"{bad"} |
    Then the command fails with exit code 2

  Scenario: PaddleOCR-VL extractor handles malformed OCR output gracefully
    Given I initialized a corpus at "corpus"
    And a fake PaddleOCR library returns malformed empty output for filename "bad.png"
    And a file "bad.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "bad.png" into corpus "corpus"
    And I build a "ocr-paddleocr-vl" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item is empty

  Scenario: PaddleOCR-VL extractor requires api_provider in API mode
    Given I initialized a corpus at "corpus"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I attempt to build a "ocr-paddleocr-vl" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: ocr-paddleocr-vl
      config:
        backend:
          mode: api
      """
    Then the command fails with exit code 2
    And standard error includes "api_provider"

  Scenario: PaddleOCR-VL API response without confidence field
    Given I initialized a corpus at "corpus"
    And a fake requests library returns HuggingFace OCR response without confidence for model "PaddlePaddle/PaddleOCR-VL" with text "No confidence"
    And the environment variable "HUGGINGFACE_API_KEY" is set to "test-key"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build an extraction run in corpus "corpus" using extractor "ocr-paddleocr-vl" with step spec "ocr-paddleocr-vl:backend={\"mode\":\"api\",\"api_provider\":\"huggingface\",\"model_id\":\"PaddlePaddle/PaddleOCR-VL\"}"
    Then the extracted text for the last ingested item equals "No confidence"

  Scenario: PaddleOCR-VL API list response without confidence field
    Given I initialized a corpus at "corpus"
    And a fake requests library returns HuggingFace list OCR response without confidence for model "PaddlePaddle/PaddleOCR-VL" with text "List no confidence"
    And the environment variable "HUGGINGFACE_API_KEY" is set to "test-key"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build an extraction run in corpus "corpus" using extractor "ocr-paddleocr-vl" with step spec "ocr-paddleocr-vl:backend={\"mode\":\"api\",\"api_provider\":\"huggingface\",\"model_id\":\"PaddlePaddle/PaddleOCR-VL\"}"
    Then the extracted text for the last ingested item equals "List no confidence"

  Scenario: PaddleOCR-VL API malformed response returns empty
    Given I initialized a corpus at "corpus"
    And a fake requests library returns "[]" for URL "https://api-inference.huggingface.co/models/PaddlePaddle/PaddleOCR-VL"
    And the environment variable "HUGGINGFACE_API_KEY" is set to "test-key"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build an extraction run in corpus "corpus" using extractor "ocr-paddleocr-vl" with step spec "ocr-paddleocr-vl:backend={\"mode\":\"api\",\"api_provider\":\"huggingface\",\"model_id\":\"PaddlePaddle/PaddleOCR-VL\"}"
    Then the extracted text for the last ingested item is empty

  Scenario: PaddleOCR-VL local mode handles malformed OCR output
    Given I initialized a corpus at "corpus"
    And a fake PaddleOCR library returns malformed output for filename "image.png"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "ocr-paddleocr-vl" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "valid"

  Scenario: PaddleOCR-VL local mode without library installed fails
    Given I initialized a corpus at "corpus"
    And the PaddleOCR library is not available
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I attempt to build a "pipeline" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: pipeline
      config:
        steps:
          - extractor_id: ocr-paddleocr-vl
            config:
              backend:
                mode: local
      """
    Then standard error includes "PaddleOCR-VL extractor (local mode) requires paddleocr"

  Scenario: PaddleOCR-VL API with unsupported provider returns empty
    Given I initialized a corpus at "corpus"
    And a fake requests library is available
    And the environment variable "OPENAI_API_KEY" is set to "test-key"
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
          - extractor_id: ocr-paddleocr-vl
            config:
              backend:
                mode: api
                api_provider: openai
                model_id: gpt-4o
      """
    Then the extracted text for the last ingested item is empty

  Scenario: PaddleOCR-VL API response with plain string format
    Given I initialized a corpus at "corpus"
    And a fake requests library returns "\"just a string\"" for URL "https://api-inference.huggingface.co/models/PaddlePaddle/PaddleOCR-VL"
    And the environment variable "HUGGINGFACE_API_KEY" is set to "test-key"
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
          - extractor_id: ocr-paddleocr-vl
            config:
              backend:
                mode: api
                api_provider: huggingface
                model_id: PaddlePaddle/PaddleOCR-VL
      """
    Then the extracted text for the last ingested item equals "just a string"

  Scenario: PaddleOCR-VL API response with list of non-dicts returns empty
    Given I initialized a corpus at "corpus"
    And a fake requests library returns "[\"string1\", \"string2\"]" for URL "https://api-inference.huggingface.co/models/PaddlePaddle/PaddleOCR-VL"
    And the environment variable "HUGGINGFACE_API_KEY" is set to "test-key"
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
          - extractor_id: ocr-paddleocr-vl
            config:
              backend:
                mode: api
                api_provider: huggingface
                model_id: PaddlePaddle/PaddleOCR-VL
      """
    Then the extracted text for the last ingested item is empty
