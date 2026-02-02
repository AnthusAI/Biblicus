Feature: Context compactor strategies
  The Context engine exposes deterministic compaction strategies for predictable budgets.

  Scenario: Truncate compactor keeps text under budget
    When I compact "one two" with truncate compactor at 3 tokens
    Then the compacted text equals "one two"

  Scenario: Truncate compactor truncates over-budget text
    When I compact "one two three" with truncate compactor at 2 tokens
    Then the compacted text equals "one two"

  Scenario: Summary compactor returns the first sentence
    When I compact "First sentence. Second sentence." with summary compactor at 10 tokens
    Then the compacted text equals "First sentence"

  Scenario: Summary compactor truncates the first sentence to budget
    When I compact "one two three four. second" with summary compactor at 2 tokens
    Then the compacted text equals "one two"

  Scenario: Summary compactor returns empty text when there are no sentences
    When I compact "<empty>" with summary compactor at 2 tokens
    Then the compacted text equals "<empty>"
