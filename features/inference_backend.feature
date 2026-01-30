Feature: Inference backend configuration
  The inference backend abstraction supports local and API execution modes.

  Scenario: API mode requires api_provider to be set
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

  Scenario: API mode with HuggingFace provider requires API key
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
          api_provider: huggingface
      """
    Then the command fails with exit code 2

  Scenario: API mode reads HuggingFace API key from environment
    Given I initialized a corpus at "corpus"
    And the environment variable "HUGGINGFACE_API_KEY" is set to "test-key"
    And a fake requests library returns HuggingFace OCR response for model "PaddlePaddle/PaddleOCR-VL" with text "Env key works"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "ocr-paddleocr-vl" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: ocr-paddleocr-vl
      config:
        backend:
          mode: api
          api_provider: huggingface
          model_id: "PaddlePaddle/PaddleOCR-VL"
      """
    Then the extracted text for the last ingested item equals "Env key works"

  Scenario: API mode reads HuggingFace API key from config file
    Given I initialized a corpus at "corpus"
    And a local Biblicus user config exists with HuggingFace API key "config-key"
    And a fake requests library returns HuggingFace OCR response for model "PaddlePaddle/PaddleOCR-VL" with text "Config key works"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "ocr-paddleocr-vl" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: ocr-paddleocr-vl
      config:
        backend:
          mode: api
          api_provider: huggingface
          model_id: "PaddlePaddle/PaddleOCR-VL"
      """
    Then the extracted text for the last ingested item equals "Config key works"

  Scenario: API mode accepts API key override in config
    Given I initialized a corpus at "corpus"
    And a fake requests library returns HuggingFace OCR response for model "PaddlePaddle/PaddleOCR-VL" with text "Override key works"
    And a file "image.png" exists with bytes:
      """
      \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82
      """
    When I ingest the file "image.png" into corpus "corpus"
    And I build a "ocr-paddleocr-vl" extraction run in corpus "corpus" using the recipe:
      """
      extractor_id: ocr-paddleocr-vl
      config:
        backend:
          mode: api
          api_provider: huggingface
          api_key: "override-key"
          model_id: "PaddlePaddle/PaddleOCR-VL"
      """
    Then the extracted text for the last ingested item equals "Override key works"

  Scenario: API mode resolves OpenAI API key from environment
    Given I initialized a corpus at "corpus"
    And the environment variable "OPENAI_API_KEY" is set to "test-openai-key"
    When I call resolve_api_key for OpenAI provider with no config override
    Then the resolved API key equals "test-openai-key"

  Scenario: API mode resolves OpenAI API key from config file
    Given I initialized a corpus at "corpus"
    And a local Biblicus user config exists with OpenAI API key "config-openai-key"
    When I call resolve_api_key for OpenAI provider with no config override
    Then the resolved API key equals "config-openai-key"

  Scenario: API mode returns None for OpenAI when no key is configured
    Given I initialized a corpus at "corpus"
    When I call resolve_api_key for OpenAI provider with no config override
    Then the resolved API key is None

  Scenario: API mode returns None for unknown provider
    Given I initialized a corpus at "corpus"
    When I call resolve_api_key for unknown provider with no config override
    Then the resolved API key is None
