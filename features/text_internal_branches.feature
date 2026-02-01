Feature: Text utilities internal helpers
  Internal helpers are deterministic and provide strict, user-facing error handling.

  Scenario: Tool loop no-tool-calls message includes assistant text
    When I build a no-tool-calls message with assistant text "not json" and current text "Hello"
    Then the no-tool-calls message includes "Assistant message:"

  Scenario: Tool loop no-tool-calls message omits assistant text when empty
    When I build a no-tool-calls message with empty assistant text and current text "Hello"
    Then the no-tool-calls message does not include "Assistant message:"

  Scenario: Text extract validation error extraction returns the first issue
    When I attempt to extract a validation error from messages:
      """
      [{"role":"user","content":"Your last edit did not validate.\nIssues:\n- Nested spans\n\nCurrent text:\n---\nHello\n---"}]
      """
    Then the extracted validation error equals "Nested spans"

  Scenario: Text extract validation error extraction ignores prompts without Issues
    When I attempt to extract a validation error from messages:
      """
      [{"role":"user","content":"Your last edit did not validate.\nCurrent text:\n---\nHello\n---"}]
      """
    Then no extracted validation error is returned

  Scenario: Text extract validation error extraction ignores prompts with Issues not on a standalone line
    When I attempt to extract a validation error from messages:
      """
      [{"role":"user","content":"Your last edit did not validate.\nIssues: - Something\nCurrent text:\n---\nHello\n---"}]
      """
    Then no extracted validation error is returned

  Scenario: Text extract validation error extraction ignores empty Issues sections
    When I attempt to extract a validation error from messages:
      """
      [{"role":"user","content":"Your last edit did not validate.\nIssues:"}]
      """
    Then no extracted validation error is returned

  Scenario: Text extract validation error extraction returns none when issues contain no bullet lines
    When I attempt to extract a validation error from messages:
      """
      [{"role":"user","content":"Your last edit did not validate.\nIssues:\nNot a bullet"}]
      """
    Then no extracted validation error is returned

  Scenario: Text extract validation error extraction skips non-bullet lines and continues searching
    When I attempt to extract a validation error from messages:
      """
      [{"role":"user","content":"Your last edit did not validate.\nIssues:\nNot a bullet\nCurrent text:\n---\nHello\n---"},{"role":"user","content":"Your last edit did not validate.\nIssues:\n- Real issue\nCurrent text:\n---\nHello\n---"}]
      """
    Then the extracted validation error equals "Real issue"
