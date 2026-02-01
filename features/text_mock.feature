Feature: Text utilities with mock markup
  The mock markup path provides deterministic text utility results for tests.

  Scenario: Mock extract spans
    When I apply mock text extract to text "Alice met Bob." with markup "Alice met <span>Bob</span>."
    Then the text extract has 1 span
    And the text extract span 1 text equals "Bob"

  Scenario: Mock extract spans with default system prompt
    When I apply mock text extract to text "Alice met Bob." with markup "Alice met <span>Bob</span>." using default system prompt
    Then the text extract has 1 span
    And the text extract span 1 text equals "Bob"

  Scenario: Mock annotate spans
    When I apply mock text annotate to text "Hello world." with markup "Hello <span label=\"greeting\">world</span>."
    Then the text annotate has 1 spans
    And the text annotate span 1 attribute "label" equals "greeting"

  Scenario: Mock annotate spans with default system prompt
    When I apply mock text annotate to text "Hello world." with markup "Hello <span label=\"greeting\">world</span>." using default system prompt
    Then the text annotate has 1 spans
    And the text annotate span 1 attribute "label" equals "greeting"

  Scenario: Mock link spans
    When I apply mock text link to text "Bob met Bob." with markup "<span id=\"link_1\">Bob</span> met <span ref=\"link_1\">Bob</span>."
    Then the text link has 2 spans
    And the text link span 1 has attribute "id" equals "link_1"
    And the text link span 2 has attribute "ref" equals "link_1"

  Scenario: Mock link spans with default system prompt
    When I apply mock text link to text "Bob met Bob." with markup "<span id=\"link_1\">Bob</span> met <span ref=\"link_1\">Bob</span>." using default system prompt
    Then the text link has 2 spans
    And the text link span 1 has attribute "id" equals "link_1"
    And the text link span 2 has attribute "ref" equals "link_1"

  Scenario: Mock redact spans
    When I apply mock text redact to text "The secret is safe." with markup "The <span>secret</span> is safe."
    Then the text redact has 1 spans

  Scenario: Mock redact spans with default system prompt
    When I apply mock text redact to text "The secret is safe." with markup "The <span>secret</span> is safe." using default system prompt
    Then the text redact has 1 spans

  Scenario: Mock slice segments
    When I apply mock text slice to text "First. Second." with markup "First.<slice/> Second."
    Then the text slice has 2 slices
    And the text slice slice 1 text equals "First."
    And the text slice slice 2 text equals " Second."

  Scenario: Mock slice segments with default system prompt
    When I apply mock text slice to text "First. Second." with markup "First.<slice/> Second." using default system prompt
    Then the text slice has 2 slices
    And the text slice slice 1 text equals "First."
    And the text slice slice 2 text equals " Second."

  Scenario: Mock extract fails when markup contains no spans
    When I attempt to apply mock text extract to text "Alice met Bob." with markup "Alice met Bob."
    Then the text utility fails with message "Text extract produced no spans"

  Scenario: Mock annotate fails when markup contains no spans
    When I attempt to apply mock text annotate to text "Hello world." with markup "Hello world."
    Then the text utility fails with message "Text annotate produced no spans"

  Scenario: Mock annotate fails when spans contain forbidden attributes
    When I attempt to apply mock text annotate to text "Hello world." with markup "Hello <span not_allowed=\"x\">world</span>."
    Then the text utility fails with message "uses attribute 'not_allowed'"

  Scenario: Mock link fails when markup contains no spans
    When I attempt to apply mock text link to text "Bob met Bob." with markup "Bob met Bob."
    Then the text utility fails with message "Text link produced no spans"

  Scenario: Mock link fails when spans contain invalid identifiers
    When I attempt to apply mock text link to text "Bob met Bob." with markup "<span id=\"wrong_1\">Bob</span> met Bob."
    Then the text utility fails with message "must start with 'link_'"

  Scenario: Mock redact fails when markup contains no spans
    When I attempt to apply mock text redact to text "The secret is safe." with markup "The secret is safe."
    Then the text utility fails with message "Text redact produced no spans"

  Scenario: Mock redact fails when spans include attributes without allowed redaction types
    When I attempt to apply mock text redact to text "The secret is safe." with markup "The <span redact=\"pii\">secret</span> is safe."
    Then the text utility fails with message "redaction types are disabled"

  Scenario: Mock slice fails when markup contains no markers
    When I attempt to apply mock text slice to text "First. Second." with markup "First. Second."
    Then the text utility fails with message "Text slice produced no markers"
