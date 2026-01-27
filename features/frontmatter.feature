Feature: Markdown front matter parsing and rendering
  Biblicus uses Yet Another Markup Language front matter for lightweight metadata on Markdown files.

  Scenario: Rendering with empty metadata returns the body unchanged
    When I render front matter with empty metadata and body "hello"
    Then the rendered markdown equals "hello"

  Scenario: Parsing without a closing fence treats it as plain text
    When I parse front matter from text without a closing fence
    Then the parsed metadata is empty
    And the parsed body starts with "---"

  Scenario: Splitting front matter returns metadata and body
    When I split front matter from markdown with title "T" and body "B"
    Then the split metadata includes title "T"
    And the split body equals "B"
