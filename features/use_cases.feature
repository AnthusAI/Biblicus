Feature: Use cases
  Use-case demos are runnable scripts that teach Biblicus by example.
  Local use cases must be deterministic and require no external services.

  Scenario: Build a context pack from a folder of notes
    When I snapshot the use case demo script "notes_to_context_pack_demo.py"
    Then the demo output includes evidence
    And the demo context pack text contains "magenta"

  Scenario: Ingest a folder of text files, extract, index, and retrieve evidence
    When I snapshot the use case demo script "text_folder_search_demo.py"
    Then the demo output includes evidence
    And the demo evidence text contains "Beta unique signal for retrieval lab."

  Scenario: Mark sensitive spans for redaction (mock mode)
    When I snapshot the use case demo script "text_redact_demo.py" with arguments:
      | arg    | value  |
      | --mock | true   |
    Then the demo marked up text contains "<span>"
    And the demo marked up text contains "</span>"

