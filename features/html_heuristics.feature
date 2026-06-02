Feature: HTML heuristic structured extraction
  Biblicus should extract article metadata and bibliography candidates from HTML using
  layered heuristics (JSON-LD, Open Graph, meta tags, reference sections, footer links)
  before optionally falling back to LLM structured extraction.

  Background:
    Given HTML heuristic fixtures are available
    And HTML LLM structured extraction is disabled

  Scenario: JSON-LD BlogPosting provides authors and publication date
    Given I parse the HTML heuristic fixture "synthetic_blog_json_ld.html"
    Then the heuristic document title is "Understanding Sequence Models"
    And the heuristic document has at least 2 authors including "Alex Example"
    And the heuristic document publication date is "2021-03-15"
    And the heuristic extraction layers include "json_ld"
    And the heuristic structured payload has at least 2 citations

  Scenario: Open Graph and Twitter card metadata is extracted
    Given I parse the HTML heuristic fixture "synthetic_news_open_graph.html"
    Then the heuristic document title is "Corpus Audit Checklist"
    And the heuristic document has at least 1 authors including "Casey Reviewer"
    And the heuristic document publication date is "2024-11-02"
    And the heuristic extraction layers include "open_graph"

  Scenario: Bibliography heading harvests reference list entries
    Given I parse the HTML heuristic fixture "synthetic_references_only.html"
    Then the heuristic document has exactly 1 authors including "Dana Writer"
    And the heuristic structured payload has at least 2 citations
    And heuristic citation 1 title contains "Baselines for retrieval"
    And the heuristic extraction layers include "reference_section"

  Scenario: Footer external links become bibliography candidates
    Given I parse the HTML heuristic fixture "synthetic_footer_links.html"
    And the heuristic fixture source uri is "https://fixture.test/articles/link-harvest"
    Then the heuristic document has at least 2 reference candidates
    And the heuristic extraction layers include "footer_element"
    And heuristic citation 1 has url "https://example.test/external/paper-a"

  Scenario: Sparse HTML does not satisfy structured sufficiency
    Given I parse the HTML heuristic fixture "synthetic_sparse.html"
    Then structured metadata sufficiency is false
    And the heuristic structured warnings include code "authors_missing"

  Scenario: Heuristic pipeline enriches web extraction without LLM
    Given I parse the HTML heuristic fixture "synthetic_blog_json_ld.html"
    And I prepare a web extraction payload with text "Fixture body text"
  When I enrich the web extraction payload with source uri "https://fixture.test/blog/sequence-models"
    Then the enriched web extraction method is "html-heuristics"
    And the enriched structured payload has at least 2 citations
    And the enriched structured payload has at least 2 authors

  Scenario: LLM fallback runs when heuristics are insufficient and LLM is enabled
    Given HTML LLM structured extraction is enabled
    And a fake HTML LLM resolver returns authors and citations for sparse pages
    And I parse the HTML heuristic fixture "synthetic_sparse.html"
    And I prepare a web extraction payload with text "Sparse body"
  When I enrich the web extraction payload with source uri "https://fixture.test/sparse"
    Then the enriched web extraction method is "llm-html"
    And the enriched structured payload has at least 1 authors
    And the enriched structured payload has at least 1 citations

  Scenario: Partial heuristics merge with LLM when sufficiency is not met
    Given HTML LLM structured extraction is enabled
    And a fake HTML LLM resolver returns only publication date
    And I parse the HTML heuristic fixture "synthetic_citations_weak.html"
    And I prepare a web extraction payload with text "Evaluation body"
  When I enrich the web extraction payload with source uri "https://fixture.test/eval"
    Then the enriched web extraction method is "html-heuristics+llm-html"
    And the enriched structured payload has at least 2 citations
    And the enriched structured publication date is "2024-01-01"

  Scenario Outline: Reference line parsing extracts years and DOI tokens
    Given a heuristic reference candidate with raw line "<raw>"
  When I normalize heuristic reference candidates
    Then normalized citation 1 year is <year>
    And normalized citation 1 doi equals <doi>

    Examples:
      | raw                                                                      | year | doi                    |
      | Morgan Demo (2018). Attention paper. doi:10.5555/1234567.89              | 2018 | 10.5555/1234567.89     |
      | Riley Test (2019). Baselines for retrieval benchmarks.                   | 2019 | none                   |

  Scenario: URL text integration uses heuristic HTML when fetch returns HTML
    Given HTML LLM structured extraction is disabled
    And the HTML heuristic fixture "synthetic_blog_json_ld.html" is served for uri "https://fixture.test/integration/blog"
  When I extract URL text from "https://fixture.test/integration/blog"
    Then the URL text extraction status is "ok"
    And the URL text extraction method is "html-heuristics"
    And the URL text structured authors count is at least 2
