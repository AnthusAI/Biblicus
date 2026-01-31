Feature: Text slice
  Text slice inserts XML slice markers into text and returns slices.

  Scenario: Text slice produces slices
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Alpha. Beta. Gamma.","new_str":"Alpha.<slice/> Beta.<slice/> Gamma."}],"done":true}
      """
    When I apply text slice to text "Alpha. Beta. Gamma."
    Then the text slice has 3 slices
    And the text slice slice 1 text equals "Alpha."
    And the text slice slice 2 text equals " Beta."
    And the text slice slice 3 text equals " Gamma."

  Scenario: Text slice supports markers at the start of text
    Given a fake OpenAI tool call is queued for "str_replace" with arguments:
      """
      {"old_str":"Alpha Beta","new_str":"<slice/>Alpha Beta"}
      """
    And a fake OpenAI tool call is queued for "done"
    When I apply text slice to text "Alpha Beta"
    Then the text slice has 1 slices
    And the text slice slice 1 text equals "Alpha Beta"

  Scenario: Text slice handles trailing markers
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Alpha","new_str":"Alpha<slice/>"}],"done":true}
      """
    When I apply text slice to text "Alpha"
    Then the text slice has 1 slices
    And the text slice slice 1 text equals "Alpha"

  Scenario: Text slice extracts paragraphs
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Para one.\\n\\nPara two.\\n\\nPara three.","new_str":"Para one.<slice/>\\n\\nPara two.<slice/>\\n\\nPara three."}],"done":true}
      """
    When I apply text slice to text "Para one.\n\nPara two.\n\nPara three."
    Then the text slice has 3 slices
    And the text slice slice 1 text equals "Para one."
    And the text slice slice 2 text equals "\n\nPara two."
    And the text slice slice 3 text equals "\n\nPara three."

  Scenario: Text slice rejects invalid edits
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"Hello<bad/>"}],"done":true}
      """
    When I attempt to apply text slice to text "Hello"
    Then the text slice error mentions "slice markers"

  Scenario: Text slice rejects non-tool responses
    Given a fake OpenAI library is available that returns chat completion "not json" for any prompt
    When I attempt to apply text slice to text "Hello"
    Then the text slice error mentions "tool calls"

  Scenario: Text slice rejects missing replacements
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Missing","new_str":"Missing<slice/>"}],"done":true}
      """
    When I attempt to apply text slice to text "Hello"
    Then the text slice error mentions "old_str not found"

  Scenario: Text slice rejects non-unique replacements
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"Hello<slice/>"}],"done":true}
      """
    When I attempt to apply text slice to text "Hello Hello"
    Then the text slice error mentions "old_str is not unique"

  Scenario: Text slice rejects empty tool arguments
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"","new_str":""}],"done":true}
      """
    When I attempt to apply text slice to text "Hello"
    Then the text slice error mentions "non-empty old_str"

  Scenario: Text slice fails when max edits per round is exceeded
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Alpha","new_str":"Alpha<slice/>"},{"command":"str_replace","old_str":"Beta","new_str":"Beta<slice/>"}],"batch":true}
      """
    When I attempt to apply text slice to text "Alpha Beta" with max rounds 1 and max edits per round 1
    Then the text slice error mentions "max edits per round"

  Scenario: Text slice rejects empty output after view
    Given a fake OpenAI tool call is queued for "view"
    And a fake OpenAI tool call is queued for "done"
    When I attempt to apply text slice to text "Hello"
    Then the text slice error mentions "produced no markers"

  Scenario: Text slice rejects unknown tools
    Given a fake OpenAI tool call is queued for "mystery"
    When I attempt to apply text slice to text "Hello"
    Then the text slice error mentions "unknown tool"

  Scenario: Text slice requires system prompt placeholder
    When I attempt to validate a text slice request with system prompt "No text here"
    Then the text slice error mentions "system_prompt must include {text}"

  Scenario: Text slice rejects prompt templates with text placeholders
    When I attempt to validate a text slice request with prompt template "Return {text}"
    Then the text slice error mentions "prompt_template must not include {text}"

  Scenario: Text slice rejects modified source text
    When I attempt to validate slice preserved text "Hello" with marked-up text "Hello<slice/>!"
    Then the text slice error mentions "modified the source text"

  Scenario: Text slice rejects empty slices
    When I attempt to apply text slice with forced empty slices
    Then the text slice error mentions "produced no slices"
