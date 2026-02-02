Feature: Context engine internal branches
  The Context engine internal helpers should be exercised for coverage.

  Scenario: Context assembler reports missing context
    When I assemble a missing Context
    Then the context error should mention "Context 'missing' not defined"

  Scenario: Context assembler uses fallback user message when none exists
    When I extract a user message from messages without a user entry
    Then the extracted user message equals "fallback"

  Scenario: Context assembler resolves templates and joins messages
    When I resolve a template with dotted fields
    Then the resolved template equals "Hello world"

  Scenario: Context assembler applies budget trimming and compaction
    When I apply context budget trimming with compact overflow
    Then the compacted system prompt equals "one two"

  Scenario: Context assembler renders retriever packs from config
    Given a retriever registry with a corpus-backed retriever
    When I render that retriever pack with a template query
    Then the rendered retriever pack equals "pack text"

  Scenario: Context assembler raises when no retriever is available
    Given a retriever registry with a corpus-backed retriever
    When I render that retriever pack without a retriever function
    Then the context error should mention "No retriever override or default retriever configured"

  Scenario: Nested context packs forbid history directives
    When I render a nested Context pack that includes history
    Then the context error should mention "Nested context packs cannot include history()"

  Scenario: Context assembler exercises default and explicit assembly paths
    When I assemble default and explicit Context paths
    Then the explicit user message equals "explicit user"
    And the default system prompt includes "base system"
