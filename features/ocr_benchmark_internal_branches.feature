Feature: OCR benchmark internal branches
  The OCR benchmark utilities should be fully exercised for coverage.

  Scenario: OCR benchmark metrics use editdistance when available
    Given a fake editdistance module is installed
    When I compute OCR benchmark metrics for ground truth "Hello world" and extracted "Hello world"
    And I compute OCR benchmark order metrics for ground truth "Hello world" and extracted "Hello world"
    And I compute OCR benchmark ngram overlap for ground truth "Hello world again" and extracted "Hello world again" with n 2
    Then OCR benchmark metrics are available

  Scenario: OCR benchmark metrics fall back without editdistance
    Given editdistance import is blocked
    When I compute OCR character accuracy for ground truth "abc" and extracted "abd"
    And I compute OCR benchmark order metrics for ground truth "<empty>" and extracted "<empty>"
    And I compute OCR benchmark order metrics for ground truth "alpha" and extracted "<empty>"
    And I compute OCR benchmark ngram overlap for ground truth "hi" and extracted "hi" with n 3
    Then OCR benchmark metrics are available

  Scenario: OCR benchmark metrics cover editdistance edge cases
    Given a fake editdistance module is installed
    When I compute OCR character accuracy for ground truth "<empty>" and extracted "<empty>"
    Then the OCR character accuracy equals 1.0

  Scenario: OCR benchmark metrics cover overlap fallback
    Given editdistance import is blocked
    When I compute OCR character accuracy for ground truth "<empty>" and extracted "x"
    Then the OCR character accuracy equals 0.0

  Scenario: OCR benchmark order metrics fall back to simple edit distance
    Given editdistance import is blocked
    When I compute OCR benchmark order metrics for ground truth "alpha beta" and extracted "alpha gamma"
    Then OCR benchmark metrics are available

  Scenario: OCR benchmark evaluation report exports outputs
    Given a fake editdistance module is installed
    When I evaluate a tiny OCR benchmark corpus with snapshot "snap-1"
    And I export the OCR benchmark report
    And I print the OCR benchmark summaries
    Then OCR benchmark report artifacts exist

  Scenario: OCR benchmark evaluation accepts explicit ground truth
    When I evaluate an OCR benchmark with explicit ground truth directory
    Then OCR benchmark metrics are available

  Scenario: OCR benchmark report handles empty CSV
    When I create an empty OCR benchmark report
    And I export the empty OCR benchmark report to CSV
    Then OCR benchmark metrics are available

  Scenario: OCR benchmark evaluation detects missing ground truth directory
    When I evaluate an OCR benchmark with missing ground truth directory
    Then the OCR benchmark error is present

  Scenario: OCR benchmark evaluation detects missing snapshot
    When I evaluate an OCR benchmark with missing snapshot
    Then the OCR benchmark error is present

  Scenario: OCR benchmark evaluation detects missing text directory
    When I evaluate an OCR benchmark with missing text directory
    Then the OCR benchmark error is present

  Scenario: OCR benchmark evaluation detects missing text files
    When I evaluate an OCR benchmark with no text files
    Then the OCR benchmark error is present

  Scenario: OCR benchmark evaluation detects missing ground truth files
    When I evaluate an OCR benchmark with missing ground truth files
    Then the OCR benchmark error is present
