Feature: Source helper internals
  Source helpers normalize filenames and namespaces for ingestion.

  Scenario: Sanitizing filenames replaces disallowed characters
    When I sanitize the filename "bad<>:"
    Then the sanitized filename equals "bad___"

  Scenario: Sanitizing filenames falls back to file when empty
    When I sanitize the filename "   "
    Then the sanitized filename equals "file"

  Scenario: Namespaced filename uses source uri when provided
    When I build a namespaced filename from source uri "http://example.com/file" and fallback "fallback" with media type "text/plain"
    Then the namespaced filename equals "http%3A%2F%2Fexample.com%2Ffile"

  Scenario: Namespaced filename uses fallback when no source uri
    When I build a namespaced filename from source uri "<empty>" and fallback "My File" with media type "text/plain"
    Then the namespaced filename equals "My File.txt"

  Scenario: Namespaced filename defaults to file when nothing provided
    When I build a namespaced filename from source uri "<empty>" and fallback "<empty>" with media type "text/plain"
    Then the namespaced filename equals "file.txt"
