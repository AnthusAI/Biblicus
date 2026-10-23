Feature: Typed application programming interface contract for Papyrus
  Papyrus calls Biblicus through typed request and response models with published JSON Schemas.
  The command-line interface is a thin wrapper that prints the response model as JSON.

  Scenario: Every Papyrus command has published schemas that match the models
    Then every Papyrus command has a published request schema and response schema
    And the published application programming interface schemas are current

  Scenario: Schema drift is reported and regeneration repairs it
    Given a scratch copy of the published application programming interface schemas
    When I edit, delete and add published schema files in the scratch copy
    Then the schema check reports the changed, missing and unexpected files
    When I regenerate the schemas into the scratch copy
    Then the scratch copy is current again with 40 schema files

  Scenario: Reindex and query output validates against the published schemas
    Given I initialized a corpus at "api-retrieval-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "api-retrieval-lab"
    And I run the command-line interface with arguments and standard input:
      """
      ["--corpus", "corpus:api-retrieval-lab", "reindex"]
      """
    Then the standard output validates against the published "reindex" response schema
    When I build a "scan" retrieval snapshot in corpus "api-retrieval-lab"
    And I run the command-line interface with arguments and standard input:
      """
      ["--corpus", "corpus:api-retrieval-lab", "query", "--query", "memory"]
      """
    Then the standard output validates against the published "query" response schema

  Scenario: Python functions return the same typed responses as the command-line interface
    Given I initialized a corpus at "api-python-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "api-python-lab"
    And I call the Python reindex function for corpus "api-python-lab"
    Then the Python reindex response reports 0 inserted items
    When I call the Python query function for "memory" against corpus "api-python-lab"
    Then the Python query fails with "No snapshot identifier provided"
    When I build a "scan" retrieval snapshot in corpus "api-python-lab"
    And I call the Python query function for "memory" against corpus "api-python-lab"
    Then the Python query response has evidence

  Scenario: Context block packs validate against the published schema from the command line and Python
    When I run the command-line interface with arguments and standard input:
      """
      ["context-pack", "build-blocks"]
      ---
      {"blocks": [{"block_id": "a", "section": "doctrine", "text": "First block."}, {"block_id": "b", "section": "evidence", "text": "Second block."}]}
      """
    Then the standard output validates against the published "context-pack-build-blocks" response schema
    When I call the Python context block function with two blocks
    Then the Python context block response text is "First block.\n\nSecond block."

  Scenario: Web metadata output validates against the published schema from the command line and Python
    When I run the command-line interface with arguments and standard input:
      """
      ["extract", "web-metadata", "--input-json", "-"]
      ---
      {"html_content": "<html><head><title>Typed Contract</title></head><body><p>Body</p></body></html>"}
      """
    Then the standard output validates against the published "extract-web-metadata" response schema
    When I call the Python web metadata function with supplied HTML
    Then the Python web metadata response has status "ok" and title "Typed Contract"

  Scenario: Steering export output validates against the published schema
    Given I initialized a corpus at "api-steering-lab"
    When I ingest the text "agent memory retrieval planning" with title "Agent Memory" and tags "agent" into corpus "api-steering-lab"
    And I build a "pipeline" extraction snapshot in corpus "api-steering-lab" with stages:
      | extractor_id       |
      | pass-through-text  |
    And I build a "scan" retrieval snapshot in corpus "api-steering-lab"
    Given a steering topic classifier seed manifest exists in corpus "api-steering-lab" for classifier "steering-classifier"
    And a steering topic-governance snapshot "governance-one" exists in corpus "api-steering-lab"
    When I export the steering bundle for corpus "api-steering-lab" with classifier "steering-classifier" and governance snapshot "governance-one"
    Then the standard output validates against the published "steering-export" response schema
    When I list steering artifacts for corpus "api-steering-lab"
    Then the standard output validates against the published "steering-artifacts" response schema

  Scenario: Seed manifest rendering output validates against the published schema
    Given a steering topic-set input "accepted-topic-set.json" exists with app-only fields
    When I render a steering seed manifest from "accepted-topic-set.json" to "seed-manifest.json"
    Then the standard output validates against the published "steering-render-seed-manifest" response schema

  Scenario: Invalid requests report every offending field clearly
    When I build a "taxonomy discover" request with a blank classifier identifier
    Then the request error says "Invalid taxonomy discover request: classifier_id: String should have at least 1 character"
    And the request error says "unknown_field: Extra inputs are not permitted"

  Scenario: Web metadata requests require a page address or HTML
    When I build a web metadata request with neither a page address nor HTML
    Then the request error says "Invalid extract web-metadata request: request: Value error, Provide source_uri and/or html_content."
