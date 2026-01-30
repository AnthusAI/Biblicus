Feature: PaddleOCR-VL API response parsing and smart override unit tests
  Unit tests for API response parsing and selection logic.

  Scenario: Parse API response with list of non-dict elements
    Given I have a PaddleOCR-VL extractor
    When I parse an API response with value ["string1", "string2"]
    Then the parsed text is empty
    And the parsed confidence is None

  Scenario: Smart override loops through extractions with low confidence
    Given I have a smart override selector
    And I have previous extractions:
      | text           | confidence |
      | First high     | 0.90       |
      | Second no conf |            |
      | Last low       | 0.40       |
    When I select the best extraction with threshold 0.70 and min length 5
    Then the selected text is "First high"
