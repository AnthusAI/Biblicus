Feature: Context Engine Errors
  As a Biblicus developer
  I want the Context engine to surface configuration errors clearly
  So that invalid settings are easy to diagnose

  Scenario: Missing compactor name raises a clear error
    Given a Context that references an unknown compactor
    When I assemble that Context expecting an error
    Then the context error should mention "Compactor 'missing' not defined"

  Scenario: Unknown compactor type raises a clear error
    Given a Context that configures an unknown compactor type
    When I assemble that Context expecting an error
    Then the context error should mention "Unknown compactor type: invalid"

  Scenario: Unknown context pack raises a clear error
    Given a Context that references an unknown pack
    When I assemble that Context expecting an error
    Then the context error should mention "Context pack 'missing_pack' is not available"

  Scenario: Base compactor requires an override
    Given a base compactor instance
    When I compact text with the base compactor
    Then the compactor error should mention "NotImplementedError"
