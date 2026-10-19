Feature: One JSON failure envelope for every typed command
  Papyrus calls the typed commands through the command line and parses what they print.
  When a typed command fails it prints exactly one JSON object on standard output with the status
  "failed" and an error carrying a code, a message and details. Standard error stays empty. The exit
  status is 2 when the request was rejected as invalid input and 1 when an accepted request failed
  during the operation.

  Scenario: Every typed command declares the failure envelope
    Then every typed command declares the failure envelope

  Scenario Outline: A rejected request prints the failure envelope and exits with status 2
    When I run the typed command with arguments '<arguments>' and standard input '<standard_input>'
    Then the command fails with exit code 2
    And standard output is one failure envelope with code "<code>"
    And the failure envelope message includes "<message>"
    And standard error is empty

    Examples:
      | arguments                                           | standard_input                                                  | code               | message                       |
      | ["extract", "url-text", "--input-json", "-"]        | not json                                                        | invalid_input_json | Invalid input JSON            |
      | ["extract", "url-text", "--input-json", "-"]        | []                                                              | invalid_input_json | Input JSON must be an object  |
      | ["extract", "url-text", "--input-json", "-"]        | {}                                                              | missing_source_uri | source_uri is required        |
      | ["extract", "url-text", "--input-json", "-"]        | {"source_uri": "https://example.org/a", "timeout_seconds": -5}  | invalid_request    | timeout_seconds               |
      | ["extract", "url-text", "--input-json", "-"]        | {"source_uri": "https://example.org/a", "timeout_seconds": "x"} | invalid_request    | timeout_seconds               |
      | ["extract", "web-metadata", "--input-json", "-"]    | not json                                                        | invalid_input_json | Invalid input JSON            |
      | ["extract", "web-metadata", "--input-json", "-"]    | {}                                                              | missing_input      | Provide source_uri            |
      | ["extract", "web-metadata", "--input-json", "-"]    | {"source_uri": "https://example.org/a", "timeout_seconds": -5}  | invalid_request    | timeout_seconds               |
      | ["extract", "web-metadata", "--input-json", "-"]    | {"html_content": "<p>x</p>", "timeout_seconds": "x"}            | invalid_request    | timeout_seconds               |
      | ["extract", "article-text", "--input-json", "-"]    | not json                                                        | invalid_input      | nonempty extracted_text       |
      | ["summarize", "map-reduce", "--task", "title", "--model", "gpt-5.4-mini-2026-03-17", "--input-json", "-"] | not json | invalid_input | nonempty extracted_text |
      | ["context-pack", "build-blocks"] | (empty) | invalid_request | request JavaScript Object Notation |
      | ["context-pack", "build-blocks"]                    | {"blocks": 3}                                                   | invalid_request    | Invalid context-pack build-blocks request |
      | ["steering", "export", "--corpus", "corpus:envelope-lab", "--classifier", ""] | (empty) | invalid_request | Invalid steering export request |

  Scenario Outline: An accepted request that fails during the operation prints the failure envelope and exits with status 1
    Given the typed operation behind "<operation>" fails
    When I run the typed command with arguments '<arguments>' and standard input '<standard_input>'
    Then the command fails with exit code 1
    And standard output is one failure envelope with code "<code>"
    And the failure envelope message includes "<message>"
    And standard error is empty

    Examples:
      | operation              | arguments                                         | standard_input                                | code                | message             |
      | url text failed result | ["extract", "url-text", "--input-json", "-"]      | {"source_uri": "https://example.org/a"}       | direct_conversion_failed | Conversion failed |
      | url text raised error  | ["extract", "url-text", "--input-json", "-"]      | {"source_uri": "https://example.org/a"}       | grobid_unreachable  | Service unreachable |
      | web metadata rejection | ["extract", "web-metadata", "--input-json", "-"]  | {"html_content": "<p>x</p>"}                  | web_metadata_failed | Page rejected       |
      | missing corpus | ["reindex", "--corpus", "corpus:missing-corpus"] | (empty) | operation_failed | Not a Biblicus corpus |

  Scenario: A failed URL extraction carries its error details and diagnostics in the envelope
    Given the typed operation behind "url text failed result" fails
    When I run the typed command with arguments '["extract", "url-text", "--input-json", "-"]' and standard input '{"source_uri": "https://example.org/a"}'
    Then the failure envelope details include "http_status" with JSON 503
    And the failure envelope details include "source_kind" with JSON "web"
    And the failure envelope details include "strategy" with JSON "markdown-then-html-then-direct"
    And the failure envelope details include "prompt_version" with JSON "test"
    And the failure envelope details include "attempts" with JSON [{"strategy": "markdown", "outcome": "failed"}]
    And the failure envelope details have exactly the keys "http_status, source_kind, strategy, content_type, prompt_version, attempts"

  Scenario Outline: A request with conflicting or missing arguments is rejected with exit status 2
    Given I initialized a corpus at "envelope-lab"
    When I run the typed command with arguments '<arguments>' and standard input '(empty)'
    Then the command fails with exit code 2
    And standard output is one failure envelope with code "invalid_request"
    And the failure envelope message includes "<message>"
    And standard error is empty

    Examples:
      | arguments | message |
      | ["--corpus", "corpus:envelope-lab", "query", "--query", "x", "--auto-deps", "--no-deps"] | cannot be combined |
      | ["--corpus", "corpus:envelope-lab", "graph", "extract", "--extractor", "cooccurrence"] | requires an extraction snapshot |

  Scenario: Commands that are not typed keep printing plain text on standard error
    When I run the command-line interface with arguments and standard input:
      """
      ["--corpus", "corpus:missing-corpus", "list"]
      """
    Then the command fails with exit code 2
    And standard output is empty
    And standard error is plain text rather than JSON

  Scenario: A successful typed command still prints its response model
    When I run the typed command with arguments '["extract", "web-metadata", "--input-json", "-"]' and standard input '{"html_content": "<html><head><title>Typed Contract</title></head><body><p>Body</p></body></html>"}'
    Then the typed command succeeds with status "ok" on standard output
    And standard error is empty
