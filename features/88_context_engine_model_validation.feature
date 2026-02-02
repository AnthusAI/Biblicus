Feature: Context engine model validation
  The Context engine models must validate configuration consistently.

  Scenario: Context budget requires ratio or max_tokens
    When I validate a Context budget with no fields
    Then the context model error should mention "Budget must specify ratio or max_tokens"

  Scenario: Pack budget requires default_ratio or default_max_tokens
    When I validate a Context pack budget with no fields
    Then the context model error should mention "Pack budget must specify default_ratio or default_max_tokens"

  Scenario: System message requires content or template
    When I validate a system message with no content or template
    Then the context model error should mention "System message must define either content or template"

  Scenario: User message requires content or template
    When I validate a user message with no content or template
    Then the context model error should mention "User message must define either content or template"

  Scenario: Assistant message requires content or template
    When I validate an assistant message with no content or template
    Then the context model error should mention "Assistant message must define either content or template"

  Scenario: Assistant message rejects both content and template
    When I validate an assistant message with content and template
    Then the context model error should mention "Assistant message must define either content or template"

  Scenario: Assistant message accepts content only
    When I validate an assistant message with content
    Then the assistant message content is "Hello assistant"

  Scenario: Context declaration normalizes string pack entry
    When I validate a Context declaration with pack "support_pack"
    Then the normalized context pack name equals "support_pack"

  Scenario: Context declaration normalizes list pack entries
    When I validate a Context declaration with pack list:
      | name        |
      | support_one |
      | support_two |
    Then the normalized context pack names include:
      | name        |
      | support_one |
      | support_two |

  Scenario: Context declaration preserves explicit pack entries
    When I validate a Context declaration with pack entries:
      | name        | weight |
      | support_one | 2.0    |
    Then the normalized context pack names include:
      | name        |
      | support_one |

  Scenario: Context declaration leaves non-list pack payloads unchanged
    When I validate a Context declaration with a pack payload map
    Then the context pack payload remains a mapping

  Scenario: Context declaration validator accepts model instances
    When I validate a Context declaration model instance
    Then the normalized context pack name equals "support_pack"

  Scenario: Context declaration validator returns model unchanged
    When I validate a Context declaration validator with a model instance
    Then the normalized context pack name equals "support_pack"
