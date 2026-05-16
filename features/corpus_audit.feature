Feature: Corpus curation audit
  A curator needs one read-only command that summarizes corpus contents,
  metadata gaps, duplicate signals, and extraction readiness.

  Scenario: Markdown audit summarizes corpus facets
    Given I initialized a corpus at "corpus"
    And a file "history.html" exists with contents:
      """
      <html><body>History article</body></html>
      """
    And a metadata file "history.yml" exists with:
      """
      title: History Article
      abstract: A short article summary.
      dates:
        published_at: "2020-01-02"
      tags:
        - ai-ml-history
        - article
      """
    When I standard-ingest the file "history.html" into corpus "corpus" with metadata file "history.yml" and source uniform resource identifier "https://example.test/history"
    And I audit corpus "corpus" as markdown
    Then standard output includes "# Corpus Audit"
    And standard output includes "Item count"
    And standard output includes "text/html"
    And standard output includes "ai-ml-history"
    And standard output includes "example.test"
    And standard output includes "2020"

  Scenario: JSON audit flags missing publication dates
    Given I initialized a corpus at "corpus"
    When I ingest the text "undated body" with title "Undated Article" and tags "ai-ml-history" into corpus "corpus"
    And I audit corpus "corpus" as JSON
    Then the corpus audit issues include code "missing-dates-published-at" for title "Undated Article"

  Scenario: Required and forbidden tag flags produce item issues
    Given I initialized a corpus at "corpus"
    When I ingest the text "wrong corpus body" with title "Wrong Corpus Article" and tags "ai-ml-research" into corpus "corpus"
    And I audit corpus "corpus" as JSON with required tag "ai-ml-history" and forbidden tag "ai-ml-research"
    Then the corpus audit issues include code "missing-required-tag" for title "Wrong Corpus Article"
    And the corpus audit issues include code "forbidden-tag" for title "Wrong Corpus Article"

  Scenario: Duplicate normalized titles are reported without failing the audit
    Given I initialized a corpus at "corpus"
    When I ingest the text "first duplicate body" with title "Same Thing" and tags "ai-ml-history" into corpus "corpus"
    And I ingest the text "second duplicate body" with title "same thing!" and tags "ai-ml-history" into corpus "corpus"
    And I audit corpus "corpus" as JSON
    Then the command succeeds
    And the corpus audit duplicates include key type "title" and key "same thing"

  Scenario: Extraction snapshot audit reports current and stale coverage
    Given I initialized a corpus at "corpus"
    When I ingest the text "first body" with title "First Article" and tags "ai-ml-history" into corpus "corpus"
    And I build a "pass-through-text" extraction snapshot in corpus "corpus"
    And I audit corpus "corpus" as JSON using the last extraction snapshot
    Then the corpus audit extraction is current with missing item count 0
    When I ingest the text "second body" with title "Second Article" and tags "ai-ml-history" into corpus "corpus"
    And I audit corpus "corpus" as JSON using the last extraction snapshot
    Then the corpus audit extraction is stale with missing item count 1
