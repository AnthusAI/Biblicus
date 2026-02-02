Feature: Text link internal helpers
  Text link provides deterministic internal helpers for validation, recovery, and rendering.

  Scenario: Coverage guidance suggests adding missing ref spans
    Given the text link errors are:
      """
      Missing linked spans for repeated text 'Acme' (1/2)
      """
    When I build text link coverage guidance
    Then the text link coverage guidance includes "Add ref spans"

  Scenario: Coverage guidance suggests adding at least one ref span
    Given the text link errors are:
      """
      Id 'link_1' must have at least one ref span
      """
    When I build text link coverage guidance
    Then the text link coverage guidance includes "ref=\"link_1\""

  Scenario: Rendering rejects overlapping spans
    When I attempt to render link span markup for text "Hello" with overlapping spans
    Then the text link internal error mentions "Span overlap"

  Scenario: Autofill ref spans returns warnings when repeated text is uncovered
    When I autofill ref spans for marked-up text "<span id=\"link_1\">Acme</span> launched. Acme updated."
    Then the autofill result includes 1 new ref spans
    And the autofill warnings include "Autofilled"

  Scenario: Promote ref spans to id when no id spans exist
    When I promote ref spans to id for text spans with id prefix "link_"
    Then the promotion warnings include "Promoted ref span"

  Scenario: Promotion leaves non-promoted ref spans untouched
    When I promote ref spans to id for multiple ref spans with id prefix "link_"
    Then the promotion warnings include "Promoted ref span"
    And the promoted spans include both id and ref spans

  Scenario: Missing coverage recovery autofills ref spans when only coverage errors exist
    When I attempt missing coverage recovery for marked-up text "<span id=\"link_1\">Acme</span> launched. Acme updated." with id prefix "link_"
    Then the missing coverage recovery returned a result
    And the missing coverage recovery warnings include "Autofilled"

  Scenario: Link span minimality rejects repeated tokens inside one span
    When I validate link span minimality for span text "Acme Acme"
    Then the link minimality errors include "repeated token"

  Scenario: Missing coverage recovery returns no result for invalid markup
    When I attempt missing coverage recovery for marked-up text "<span id=\"link_1\">Acme" with id prefix "link_"
    Then the missing coverage recovery returned no result

  Scenario: Coverage guidance suggests structuring repeated text with id + refs
    Given the text link errors are:
      """
      Repeated text 'Acme' must include ref spans for repeats
      """
    When I build text link coverage guidance
    Then the text link coverage guidance includes "one id"

  Scenario: Coverage guidance suggests matching id and ref span text
    Given the text link errors are:
      """
      Id 'link_1' span text must match ref span text (id: 'Acme', ref: 'ACME')
      """
    When I build text link coverage guidance
    Then the text link coverage guidance includes "exact same text"

  Scenario: Promote ref spans skips refs without the required id prefix
    When I promote ref spans to id for text spans with ref value "bad_1" and id prefix "link_"
    Then the promotion warnings are empty

  Scenario: Link span validation reports repeated-text constraints
    When I validate link spans with mismatched id/ref texts
    Then the link span errors include "Ref spans for id 'link_1' must wrap the same text"
    And the link span errors include "span text must match ref span text"

  Scenario: Link span validation reports repeated-text grouping errors
    When I validate link spans with repeated text requiring exactly one id
    Then the link span errors include "must have exactly one id span"
    When I validate link spans with repeated text missing ref spans
    Then the link span errors include "must include ref spans for repeats"
    When I validate link spans with repeated refs that do not match ids
    Then the link span errors include "refs must match id"

  Scenario: Link coverage validation ignores empty span text
    When I validate link coverage for empty span text
    Then the link coverage errors are empty

  Scenario: Link minimality validation ignores spans with no word tokens
    When I validate link span minimality for span text "!!!"
    Then the link minimality errors are empty

  Scenario: Autofill ref spans returns no result when id spans have empty text
    When I attempt to autofill ref spans for empty id span text
    Then the autofill returned no result

  Scenario: Rendering includes plain span tags when attributes are empty
    When I render span markup for text "Hello" with an attribute-less span
    Then the rendered markup equals "<span>Hello</span>"

  Scenario: Replacement rejects span tags in the target text
    When I attempt to replace "<span>Acme</span>" with "<span id=\"link_1\">Acme</span>" in the text "<span>Acme</span> launched"
    Then the replacement error mentions "must target plain text without span tags"

  Scenario: Retry message includes guidance for nested spans
    When I build a text link retry message with nested span errors
    Then the retry message includes "Do not create nested or overlapping spans"

  Scenario: Missing coverage only classification includes repeated-text errors
    When I classify repeated-text errors as coverage-only
    Then the repeated-text error is treated as coverage-only

  Scenario: Missing coverage recovery can bail out when autofill produces invalid output
    When I attempt missing coverage recovery where autofill produces invalid spans
    Then the missing coverage recovery returned no result
