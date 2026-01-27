Feature: Command-line interface entry point
  The module entry point should execute with standard command-line interface behavior.

  Scenario: Running the module entry point prints help
    When I run the biblicus module with "--help"
    Then the command succeeds
