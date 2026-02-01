Feature: Text redact
  Text redact inserts XML span tags to mark redacted text.

  Scenario: Text redact produces spans without attributes
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"SSN","new_str":"<span>SSN</span>"}],"done":true}
      """
    When I apply text redact to text "SSN: 123" without redaction types
    Then the text redact has 1 spans
    And the text redact span 1 text equals "SSN"

  Scenario: Text redact uses redaction types when configured
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Account","new_str":"<span redact=\"pii\">Account</span>"}],"done":true}
      """
    When I apply text redact to text "Account: 123" with redaction types "pii,pci"
    Then the text redact has 1 spans
    And the text redact span 1 has attribute "redact" equals "pii"

  Scenario: Text redact rejects attributes when redaction types are disabled
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Account","new_str":"<span redact=\"pii\">Account</span>"}],"done":true}
      """
    When I attempt to apply text redact to text "Account" without redaction types
    Then the text redact error mentions "attributes but redaction types are disabled"

  Scenario: Text redact rejects unsupported attribute name
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Account","new_str":"<span label=\"pii\">Account</span>"}],"done":true}
      """
    When I attempt to apply text redact to text "Account" with redaction types "pii,pci"
    Then the text redact error mentions "only 'redact' is allowed"

  Scenario: Text redact rejects unsupported redaction type
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Account","new_str":"<span redact=\"secret\">Account</span>"}],"done":true}
      """
    When I attempt to apply text redact to text "Account" with redaction types "pii,pci"
    Then the text redact error mentions "Allowed types"

  Scenario: Text redact rejects missing redact attribute
    Given a fake OpenAI library is available that returns chat completion for prompt containing "Current text":
      """
      {"operations":[{"command":"str_replace","old_str":"Account","new_str":"<span label=\"pii\" other=\"x\">Account</span>"}],"done":true}
      """
    When I attempt to apply text redact to text "Account" with redaction types "pii"
    Then the text redact error mentions "exactly one redact attribute"

  Scenario: Text redact rejects invalid span markup
    When I attempt to validate redact markup:
      """
      <span>Account
      """
    Then the text redact error mentions "unclosed span"

  Scenario: Text redact retry message includes span context
    Given the text redact retry errors are:
      """
      Span 1 contains attributes but redaction types are disabled
      """
    When I build a text redact retry message for markup:
      """
      <span redact="pii">Account</span>
      """
    Then the text redact retry message includes span context
    And the text redact retry message includes "Span 1: Account"

  Scenario: Text redact warns when the tool loop does not call done
    When I apply text redact with a non-done tool loop result
    Then the text redact warnings include max rounds

  Scenario: Text redact warns when confirmation reaches max rounds without done
    Given a fake OpenAI library is available
    And a fake OpenAI tool call is queued for "view"
    And a fake OpenAI tool call is queued for "view"
    And a fake OpenAI tool call is queued for "view"
    And a fake OpenAI tool call is queued for "view"
    And a fake OpenAI tool call is queued for "view"
    And a fake OpenAI tool call is queued for "view"
    And a fake OpenAI tool call is queued for "view"
    And a fake OpenAI tool call is queued for "view"
    When I apply text redact to text "Account" without redaction types
    Then the text redact warnings include "Text redact reached max rounds without done=true"
    And the text redact warnings include "Text redact confirmation reached max rounds without done=true"
    And the text redact has 0 spans

  Scenario: Text redact surfaces tool loop errors with done
    When I attempt text redact with a tool loop error and done
    Then the text redact error mentions "tool loop error"

  Scenario: Text redact confirms when no spans are produced
    When I attempt text redact with no spans and done
    Then the text redact warnings include "Text redact returned no spans; model confirmed empty result"
    And the text redact has 0 spans

  Scenario: Text redact warns when confirmation reaches max rounds without done in the confirmation loop
    When I apply text redact with no edits and confirmation reaches max rounds without done
    Then the text redact warnings include "Text redact confirmation reached max rounds without done=true"
    And the text redact warnings include "Text redact returned no spans; model confirmed empty result"
    And the text redact has 0 spans

  Scenario: Text redact allows confirmation to insert spans after an empty first pass
    When I apply text redact with no edits and confirmation inserts spans
    Then the text redact has at least 1 spans

  Scenario: Text redact surfaces confirmation last_error as a failure
    When I attempt text redact where confirmation fails with a last error
    Then the text redact error mentions "Text redact failed: confirmation error"

  Scenario: Text redact validates spans after the tool loop
    When I attempt text redact with invalid spans after the tool loop
    Then the text redact error mentions "Allowed types"

  Scenario: Text redact validates spans after confirmation
    When I attempt text redact with invalid spans in confirmation
    Then the text redact error mentions "Allowed types"

  Scenario: Text redact rejects missing or non-unique replacements
    When I attempt redact replace with old_str "Missing" and new_str "<span>Missing</span>"
    Then the text redact error mentions "old_str not found"
    When I attempt redact replace with old_str "Account" and new_str "<span>Account</span>"
    Then the text redact error mentions "old_str is not unique"

  Scenario: Text redact rejects replacement text changes
    When I attempt redact replace in text "Account" with old_str "Account" and new_str "<span>Account!</span>"
    Then the text redact error mentions "may only insert span tags"

  Scenario: Text redact rejects preserved text changes
    When I attempt to validate redact preservation with original "Account" and marked up "<span>Account!</span>"
    Then the text redact error mentions "modified the source text"
