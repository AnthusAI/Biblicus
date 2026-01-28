Feature: Hook execution error handling
  Hooks must return validated Pydantic results.
  A misbehaving hook must fail with a clear error.

  Scenario: Non-Pydantic hook result raises a clear error
    When I execute a hook manager with a non-Pydantic hook result
    Then a hook result error is raised

  Scenario: Base hook run is not implemented
    When I call the base lifecycle hook run method
    Then a hook not implemented error is raised

  Scenario: Hook exceptions are wrapped with a clear error
    When I execute a hook manager with a hook that raises an exception
    Then a hook execution error is raised
