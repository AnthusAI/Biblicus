Feature: Markov boundary segments
  As a pipeline author
  I want deterministic START/END boundary segments
  So that Markov sequences have explicit call boundaries

  Scenario: START and END boundaries are added per item
    When I add boundary segments to a two-segment item
    Then the first segment equals "START"
    Then the last segment equals "END"
    Then the boundary segments are added
