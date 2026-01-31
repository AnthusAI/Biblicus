Feature: Text extract
  Text extract inserts XML span tags into text and returns spans.

  Scenario: Text extract produces spans
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span>Hello</span>"}],"done":true}
      """
    When I apply text extract to text "Hello world"
    Then the text extract has 1 span
    And the first span text equals "Hello"
    And the text extract marked-up text equals "<span>Hello</span> world"

  Scenario: Text extract extracts paragraphs
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Para one.","new_str":"<span>Para one.</span>"},{"command":"str_replace","old_str":"Para two.","new_str":"<span>Para two.</span>"},{"command":"str_replace","old_str":"Para three.","new_str":"<span>Para three.</span>"}],"done":true}
      """
    When I apply text extract to text:
      """
      Para one.

      Para two.

      Para three.
      """
    Then the text extract has 3 span
    And the text extract span 1 text equals "Para one."
    And the text extract span 2 text equals "Para two."
    And the text extract span 3 text equals "Para three."

  Scenario: Text extract extracts first sentences per paragraph
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"First one.","new_str":"<span>First one.</span>"},{"command":"str_replace","old_str":"Alpha first.","new_str":"<span>Alpha first.</span>"}],"done":true}
      """
    When I apply text extract to text:
      """
      First one. Second one.

      Alpha first. Alpha second.
      """
    Then the text extract has 2 span
    And the text extract span 1 text equals "First one."
    And the text extract span 2 text equals "Alpha first."

  Scenario: Text extract extracts money quotes
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"\"I will pay $20 today.\"","new_str":"<span>\"I will pay $20 today.\"</span>"}],"done":true}
      """
    When I apply text extract to text:
      """
      She said "I will pay $20 today." Then she left.
      """
    Then the text extract has 1 span
    And the text extract has a span containing "$20"

  Scenario: Text extract wraps verbs
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"can","new_str":"<span>can</span>"},{"command":"str_replace","old_str":"try","new_str":"<span>try</span>"},{"command":"str_replace","old_str":"get","new_str":"<span>get</span>"},{"command":"str_replace","old_str":"promise","new_str":"<span>promise</span>"}],"done":true}
      """
    When I apply text extract to text "I can try to get help, but I promise nothing."
    Then the text extract has 4 span
    And the text extract span 1 text equals "can"
    And the text extract span 2 text equals "try"
    And the text extract span 3 text equals "get"
    And the text extract span 4 text equals "promise"

  Scenario: Text extract rejects invalid edits
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<bad>Hello</bad>"}],"done":true}
      """
    When I attempt to apply text extract to text "Hello"
    Then the text extract error mentions "span tags"

  Scenario: Text extract rejects non-tool responses
    Given a fake OpenAI library is available that returns chat completion "not json" for any prompt
    When I attempt to apply text extract to text "Hello"
    Then the text extract error mentions "tool calls"

  Scenario: Text extract rejects unsupported providers
    When I attempt to apply text extract using provider "bedrock" on text "Hello"
    Then the text extract error mentions "Unsupported provider"

  Scenario: Text extract fails when OpenAI dependency is unavailable
    Given the OpenAI dependency is unavailable
    When I attempt to apply text extract to text "Hello"
    Then the text extract error mentions "biblicus[openai]"

  Scenario: Text extract rejects missing replacements
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Missing","new_str":"<span>Missing</span>"}],"done":true}
      """
    When I attempt to apply text extract to text "Hello"
    Then the text extract error mentions "old_str not found"

  Scenario: Text extract rejects non-unique replacements
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span>Hello</span>"}],"done":true}
      """
    When I attempt to apply text extract to text "Hello Hello"
    Then the text extract error mentions "old_str is not unique"

  Scenario: Text extract rejects nested spans
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span><span>Hello</span></span>"}],"done":true}
      """
    When I attempt to apply text extract to text "Hello"
    Then the text extract error mentions "nested spans"

  Scenario: Text extract rejects unmatched closing tags
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"Hello</span>"}],"done":true}
      """
    When I attempt to apply text extract to text "Hello"
    Then the text extract error mentions "unmatched closing tag"

  Scenario: Text extract rejects unclosed spans
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span>Hello"}],"done":true}
      """
    When I attempt to apply text extract to text "Hello"
    Then the text extract error mentions "unclosed span"

  Scenario: Text extract rejects empty tool arguments
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"","new_str":""}],"done":true}
      """
    When I attempt to apply text extract to text "Hello"
    Then the text extract error mentions "non-empty old_str"

  Scenario: Text extract fails when max edits per round is exceeded
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Alpha","new_str":"<span>Alpha</span>"},{"command":"str_replace","old_str":"Beta","new_str":"<span>Beta</span>"}],"batch":true}
      """
    When I attempt to apply text extract to text "Alpha Beta" with max rounds 1 and max edits per round 1
    Then the text extract error mentions "max edits per round"

  Scenario: Text extract warns when max rounds are reached without done
    Given a fake OpenAI tool call is queued for "str_replace" with arguments:
      """
      {"old_str":"Alpha beta","new_str":"<span>Alpha</span> beta"}
      """
    When I attempt to apply text extract to text "Alpha beta" with max rounds 1 and max edits per round 1
    Then the text extract warnings include "Text extract reached max rounds without done=true"
    And the text extract has 1 span

  Scenario: Text extract rejects empty output after view
    Given a fake OpenAI tool call is queued for "view"
    And a fake OpenAI tool call is queued for "done"
    When I attempt to apply text extract to text "Hello"
    Then the text extract error mentions "produced no spans"

  Scenario: Text extract rejects unknown tools
    Given a fake OpenAI tool call is queued for "mystery"
    When I attempt to apply text extract to text "Hello"
    Then the text extract error mentions "unknown tool"

  Scenario: Text extract requires system prompt placeholder
    When I attempt to validate a text extract request with system prompt "No text here"
    Then the text extract error mentions "system_prompt must include {text}"

  Scenario: Text extract rejects prompt templates with text placeholders
    When I attempt to validate a text extract request with prompt template "Return {text}"
    Then the text extract error mentions "prompt_template must not include {text}"

  Scenario: Text extract rejects modified source text
    When I attempt to validate preserved text "Hello" with marked-up text "Hello<span>!</span>"
    Then the text extract error mentions "modified the source text"
