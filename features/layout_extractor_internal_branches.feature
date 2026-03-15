Feature: Layout extractors internal branches
  Layout-oriented extractors should exercise dependency and branch paths.

  Scenario: Mock layout detector rejects invalid layout type
    When I validate mock layout detector config with layout_type "invalid"
    Then the mock layout detector config validation fails

  Scenario: Mock layout detector skips non-image items
    When I run mock layout detector on a non-image item
    Then the mock layout detector returns no extraction

  Scenario: Heron layout extractor runs with fake dependencies
    Given fake Heron layout dependencies are installed
    When I run the Heron layout extractor on a sample image
    Then Heron layout metadata includes regions

  Scenario: Heron layout extractor handles non-image and base model
    Given fake Heron layout dependencies are installed
    When I run the Heron layout extractor on a non-image item
    Then Heron layout extraction returns no result
    When I run the Heron layout extractor with the base model
    Then Heron layout metadata includes regions

  Scenario: Heron layout extractor handles empty results
    Given fake Heron layout dependencies are installed
    When I run the Heron layout extractor with empty results
    Then Heron layout metadata is present

  Scenario: Heron layout extractor reports missing image
    Given fake Heron layout dependencies are installed
    When I run the Heron layout extractor with a missing image
    Then Heron layout extraction fails

  Scenario: Heron layout extractor fails without dependencies
    Given Heron layout dependencies are unavailable
    When I validate the Heron layout extractor configuration
    Then Heron layout extraction fails

  Scenario: PaddleOCR layout extractor runs with fake dependencies
    Given fake PaddleOCR layout dependencies are installed
    When I run the PaddleOCR layout extractor on a sample image
    And I parse a PaddleOCR layout region
    Then PaddleOCR layout metadata includes regions

  Scenario: PaddleOCR layout extractor handles empty and non-image cases
    Given fake PaddleOCR layout dependencies are installed
    When I run the PaddleOCR layout extractor on a non-image item
    Then PaddleOCR layout extraction returns no result
    When I run the PaddleOCR layout extractor with empty results
    Then PaddleOCR layout metadata is present

  Scenario: PaddleOCR layout extractor handles missing coordinates
    When I run the PaddleOCR layout extractor with missing coordinates
    Then PaddleOCR layout includes an empty bbox region

  Scenario: PaddleOCR layout extractor handles non-dict page results
    Given fake PaddleOCR layout dependencies are installed
    When I run the PaddleOCR layout extractor with a non-dict page result
    Then PaddleOCR layout has no regions

  Scenario: PaddleOCR layout extractor reports missing image
    Given fake PaddleOCR layout dependencies are installed
    When I run the PaddleOCR layout extractor with a missing image
    Then PaddleOCR layout extraction fails

  Scenario: PaddleOCR layout extractor fails without dependencies
    Given PaddleOCR layout dependencies are unavailable
    When I validate the PaddleOCR layout extractor configuration
    Then PaddleOCR layout extraction fails

  Scenario: PaddleOCR-VL handles dict API responses
    Given a fake PaddleOCR library is available that returns dict output for filename "image.png"
    When I run PaddleOCR-VL extraction on "image.png"
    Then PaddleOCR-VL extraction returns text "Line A\nLine B"

  Scenario: PaddleOCR-VL handles mixed dict output
    Given a fake PaddleOCR library returns mixed dict output for filename "image.png"
    When I run PaddleOCR-VL extraction on "image.png"
    Then PaddleOCR-VL extraction returns text "<empty>"

  Scenario: PaddleOCR-VL skips unknown page results
    Given a fake PaddleOCR library returns an unknown page result for filename "image.png"
    When I run PaddleOCR-VL extraction on "image.png"
    Then PaddleOCR-VL extraction returns text "<empty>"
