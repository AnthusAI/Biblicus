Feature: Embedding index evidence fallback
  Embedding index backends should fall back to span extraction when snippets are missing.

  Scenario: In-memory retriever falls back to span extraction when snippets are missing
    When I build in-memory evidence for a non-text item
    Then the evidence text equals "a"

  Scenario: File retriever falls back to span extraction when snippets are missing
    When I build file-backed evidence for a non-text item
    Then the evidence text equals "a"
