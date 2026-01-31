Feature: Text utilities
  Agentic text utilities use a virtual file edit loop to transform text.

  Scenario: Text extract wraps returned text
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span>Hello</span>"}],"done":true}
      """
    When I apply text extract to text "Hello world"
    Then the text extract has 1 span

  Scenario: Text slice splits text at slice markers
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Alpha","new_str":"Alpha<slice/>"}],"done":true}
      """
    When I apply text slice to text "Alpha Beta"
    Then the text slice has 2 slices

  Scenario: Text annotate adds labeled spans
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Hello","new_str":"<span label=\"greeting\">Hello</span>"}],"done":true}
      """
    When I apply text annotate to text "Hello world"
    Then the text annotate has 1 spans

  Scenario: Text redact adds redaction spans
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Secret","new_str":"<span>Secret</span>"}],"done":true}
      """
    When I apply text redact to text "Secret data" without redaction types
    Then the text redact has 1 spans

  Scenario: Text link adds id/ref spans
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Acme shipped.","new_str":"<span id=\"link_1\">Acme shipped.</span>"},{"command":"str_replace","old_str":"Acme sold.","new_str":"<span ref=\"link_1\">Acme sold.</span>"}],"done":true}
      """
    When I apply text link to text "Acme shipped. Acme sold."
    Then the text link has 2 spans

  Scenario: Tool loop custom retry message uses caller builder
    When I build a tool loop retry message with a custom builder
    Then the tool loop retry message equals "Custom: 1 errors in Text"

  Scenario: Tool loop default retry message includes validation errors
    When I build a tool loop retry message with default builder
    Then the tool loop retry message includes "Your last edit did not validate."
    And the tool loop retry message includes "- Missing span"
