Feature: Text link
  Text link inserts id and ref span tags to connect repeated mentions.

  Scenario: Text link produces id/ref spans
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Acme launched.","new_str":"<span id=\"link_1\">Acme launched.</span>"},{"command":"str_replace","old_str":"Acme updated.","new_str":"<span ref=\"link_1\">Acme updated.</span>"}],"done":true}
      """
    When I apply text link to text "Acme launched. Acme updated."
    Then the text link has 2 spans
    And the text link span 1 has attribute "id" equals "link_1"
    And the text link span 2 has attribute "ref" equals "link_1"

  Scenario: Text link rejects ref before id
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Acme","new_str":"<span ref=\"link_1\">Acme</span>"}],"done":true}
      """
    When I attempt to apply text link to text "Acme"
    Then the text link error mentions "does not match a previous id"

  Scenario: Text link rejects invalid id prefix
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Acme","new_str":"<span id=\"bad_1\">Acme</span>"}],"done":true}
      """
    When I attempt to apply text link to text "Acme"
    Then the text link error mentions "must start"

  Scenario: Text link rejects duplicate ids
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Acme one.","new_str":"<span id=\"link_1\">Acme one.</span>"},{"command":"str_replace","old_str":"Acme two.","new_str":"<span id=\"link_1\">Acme two.</span>"}],"done":true,"batch":true}
      """
    When I attempt to apply text link to text "Acme one. Acme two."
    Then the text link error mentions "duplicate id"

  Scenario: Text link rejects unsupported attributes
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Acme","new_str":"<span label=\"x\">Acme</span>"}],"done":true}
      """
    When I attempt to apply text link to text "Acme"
    Then the text link error mentions "only 'id' or 'ref'"

  Scenario: Text link rejects multiple attributes
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Acme","new_str":"<span id=\"link_1\" ref=\"link_2\">Acme</span>"}],"done":true}
      """
    When I attempt to apply text link to text "Acme"
    Then the text link error mentions "exactly one attribute"

  Scenario: Text link rejects empty attribute values
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Acme","new_str":"<span id=\"\">Acme</span>"}],"done":true}
      """
    When I attempt to apply text link to text "Acme"
    Then the text link error mentions "empty value"

  Scenario: Text link rejects invalid span markup
    When I attempt to validate link markup:
      """
      <span id="link_1">Acme
      """
    Then the text link error mentions "unclosed span"

  Scenario: Text link retry message includes span context
    Given the text link retry errors are:
      """
      Span 1 uses attribute 'label' but only 'id' or 'ref' are allowed
      """
    When I build a text link retry message for markup:
      """
      <span label="x">Hello</span>
      """
    Then the text link retry message includes span context
    And the text link retry message includes "Span 1: Hello"

  Scenario: Text link warns when the tool loop does not call done
    When I apply text link with a non-done tool loop result
    Then the text link warnings include max rounds

  Scenario: Text link surfaces tool loop errors with done
    When I attempt text link with a tool loop error and done
    Then the text link error mentions "tool loop error"

  Scenario: Text link fails when no spans are produced
    When I attempt text link with no spans and done
    Then the text link error mentions "produced no spans"

  Scenario: Text link validates spans after the tool loop
    When I attempt text link with invalid spans after the tool loop
    Then the text link error mentions "only 'id' or 'ref'"

  Scenario: Text link rejects missing or non-unique replacements
    When I attempt link replace with old_str "Missing" and new_str "<span id=\"link_1\">Missing</span>"
    Then the text link error mentions "old_str not found"
    When I attempt link replace with old_str "Acme" and new_str "<span id=\"link_1\">Acme</span>"
    Then the text link error mentions "old_str is not unique"

  Scenario: Text link rejects replacement text changes
    When I attempt link replace in text "Hello" with old_str "Hello" and new_str "<span>Hello!</span>"
    Then the text link error mentions "may only insert span tags"

  Scenario: Text link rejects preserved text changes
    When I attempt to validate link preservation with original "Acme" and marked up "<span id=\"link_1\">Acme!</span>"
    Then the text link error mentions "modified the source text"
