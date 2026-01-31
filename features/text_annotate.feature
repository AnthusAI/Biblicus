Feature: Text annotate
  Text annotate inserts XML span tags with attributes and returns structured spans.

  Scenario: Text annotate produces labeled spans
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span label=\"greeting\">Hello</span>"}],"done":true}
      """
    When I apply text annotate to text "Hello world"
    Then the text annotate has 1 spans
    And the text annotate span 1 text equals "Hello"
    And the text annotate span 1 attribute "label" equals "greeting"

  Scenario: Text annotate accepts custom allowed attributes
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Alpha","new_str":"<span category=\"letter\">Alpha</span>"}],"done":true}
      """
    When I apply text annotate to text "Alpha beta" with allowed attributes "category" and prompt template:
      """
      Return the requested text.
      """
    Then the text annotate has 1 spans
    And the text annotate span 1 attribute "category" equals "letter"

  Scenario: Text annotate rejects missing attributes
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span>Hello</span>"}],"done":true}
      """
    When I attempt to apply text annotate to text "Hello"
    Then the text annotate error mentions "missing an attribute"

  Scenario: Text annotate rejects unsupported attributes
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span wrong=\"x\">Hello</span>"}],"done":true}
      """
    When I attempt to apply text annotate to text "Hello"
    Then the text annotate error mentions "Allowed attributes"

  Scenario: Text annotate rejects empty attribute values
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span label=\"\">Hello</span>"}],"done":true}
      """
    When I attempt to apply text annotate to text "Hello"
    Then the text annotate error mentions "empty value"

  Scenario: Text annotate rejects multiple attributes
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span label=\"x\" phase=\"y\">Hello</span>"}],"done":true}
      """
    When I attempt to apply text annotate to text "Hello"
    Then the text annotate error mentions "multiple attributes"

  Scenario: Text annotate rejects nested spans
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span label=\"x\"><span label=\"y\">Hello</span></span>"}],"done":true}
      """
    When I attempt to apply text annotate to text "Hello"
    Then the text annotate error mentions "nested spans"

  Scenario: Text annotate rejects duplicate attributes
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span label=\"x\" label=\"y\">Hello</span>"}],"done":true}
      """
    When I attempt to apply text annotate to text "Hello"
    Then the text annotate error mentions "duplicate span attributes"

  Scenario: Text annotate rejects unsupported attributes in tags
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span label=\"x\" bogus>Hello</span>"}],"done":true}
      """
    When I attempt to apply text annotate to text "Hello"
    Then the text annotate error mentions "unsupported span attributes"

  Scenario: Text annotate rejects unmatched closing tags
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"Hello</span>"}],"done":true}
      """
    When I attempt to apply text annotate to text "Hello"
    Then the text annotate error mentions "unmatched closing tag"

  Scenario: Text annotate rejects unclosed spans
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span label=\"x\">Hello"}],"done":true}
      """
    When I attempt to apply text annotate to text "Hello"
    Then the text annotate error mentions "unclosed span"

  Scenario: Text annotate rejects modified text
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span label=\"x\">Hello!</span>"}],"done":true}
      """
    When I attempt to apply text annotate to text "Hello"
    Then the text annotate error mentions "may only insert span tags"

  Scenario: Text annotate rejects invalid span tags
    When I attempt to parse a span tag:
      """
      <span
      """
    Then the span parse error mentions "invalid span tag"

  Scenario: Text annotate retry message includes span context
    Given the text annotate retry errors are:
      """
      Span 1 uses attribute 'wrong'. Allowed attributes: label
      """
    When I build a text annotate retry message for markup:
      """
      <span label="wrong">Hello</span>
      """
    Then the text annotate retry message includes span context
    And the text annotate retry message includes "Span 1: Hello"

  Scenario: Text annotate warns when the tool loop does not call done
    When I apply text annotate with a non-done tool loop result
    Then the text annotate warnings include max rounds

  Scenario: Text annotate surfaces tool loop errors with done
    When I attempt text annotate with a tool loop error and done
    Then the text annotate error mentions "tool loop error"

  Scenario: Text annotate fails when no spans are produced
    When I attempt text annotate with no spans and done
    Then the text annotate error mentions "produced no spans"

  Scenario: Text annotate validates spans after the tool loop
    When I attempt text annotate with invalid spans after the tool loop
    Then the text annotate error mentions "Allowed attributes"

  Scenario: Text annotate rejects missing or non-unique replacements
    When I attempt annotate replace with old_str "Missing" and new_str "<span label=\"x\">Missing</span>"
    Then the text annotate error mentions "old_str not found"
    When I attempt annotate replace with old_str "Hello" and new_str "<span label=\"x\">Hello</span>"
    Then the text annotate error mentions "old_str is not unique"

  Scenario: Text annotate rejects preserved text changes
    When I attempt to validate annotate preservation with original "Hello" and marked up "<span label=\"x\">Hello!</span>"
    Then the text annotate error mentions "modified the source text"

  Scenario: Span context section is empty when no indices are found
    Given the text annotate retry errors are:
      """
      No span indices here
      """
    When I build a span context section for markup:
      """
      <span label="x">Hello</span>
      """
    Then the span context section is empty

  Scenario: Span context section is empty when markup is invalid
    Given the text annotate retry errors are:
      """
      Span 1 uses attribute 'x'
      """
    When I build a span context section for markup:
      """
      <span label="x">Hello
      """
    Then the span context section is empty

  Scenario: Span context section is empty when summaries are empty
    Given the text annotate retry errors are:
      """
      Span 2 uses attribute 'x'
      """
    When I build a span context section for markup:
      """
      <span label="x">Hello</span><span label="y">   </span>
      """
    Then the span context section is empty

  Scenario: Span context section is empty when span indices are missing
    Given the text annotate retry errors are:
      """
      Span 3 uses attribute 'x'
      """
    When I build a span context section for markup:
      """
      <span label="x">Hello</span>
      """
    Then the span context section is empty
