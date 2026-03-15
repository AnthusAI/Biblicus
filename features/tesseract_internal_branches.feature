Feature: Tesseract extractor internal branches
  Tesseract error paths should be covered.

  Scenario: Tesseract extractor fails when pytesseract is missing
    Given pytesseract import is blocked
    When I validate the tesseract extractor configuration
    Then the tesseract extractor validation fails

  Scenario: Tesseract extractor fails when tesseract binary is missing
    Given a fake pytesseract module raises on version check
    When I validate the tesseract extractor configuration
    Then the tesseract extractor validation fails

  Scenario: Tesseract layout extraction skips invalid regions
    When I extract tesseract text with layout metadata and invalid regions
    Then the tesseract layout extraction is empty

  Scenario: Tesseract layout extraction falls back without regions
    When I extract tesseract text without layout regions
    Then the tesseract extraction is empty

  Scenario: Tesseract full-image extraction skips blank words
    When I extract tesseract text from a full image with blank words
    Then the tesseract extraction excludes blank words

  Scenario: Tesseract full-image extraction skips blank words
    When I extract tesseract text from a full image with blank words
    Then the tesseract extraction excludes blank words
