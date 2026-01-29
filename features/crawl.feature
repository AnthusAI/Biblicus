Feature: Crawling a website into a corpus
  Corpus operators can build a corpus by crawling a website prefix.
  Crawled content is ingested as immutable raw items, with derived metadata stored in sidecars.

  Scenario: Crawl ingests linked pages under the allowed prefix
    Given I initialized a corpus at "corpus"
    And a hypertext transfer protocol server is serving the workdir
    And a file "site/index.html" exists with contents:
      """
      <html>
        <body>
          <a href="page.html">Page</a>
          <a href="page.html">Page again</a>
          <a href="subdir/">Subdir</a>
          <a href="blob.bin">Binary</a>
          <a name="anchor">Anchor</a>
          <img src="" alt="empty" />
          <a href="/outside.html">Outside</a>
          <a href="mailto:test@example.com">Email</a>
        </body>
      </html>
      """
    And a file "site/page.html" exists with contents:
      """
      <html><body>hello</body></html>
      """
    And a file "site/subdir/index.html" exists with contents:
      """
      <html><body>subdir</body></html>
      """
    And a binary file "site/blob.bin" exists
    And a file "outside.html" exists with contents:
      """
      <html><body>outside</body></html>
      """
    When I crawl the hypertext transfer protocol uniform resource locator "site/index.html" with allowed prefix "site/" into corpus "corpus"
    Then the crawl reports stored_items 4
    And the crawl reports skipped_outside_prefix_items 1
    And the corpus contains a crawled item with source uniform resource identifier ending with "site/index.html"
    And the corpus contains a crawled item with source uniform resource identifier ending with "site/page.html"
    And the corpus contains a crawled item with source uniform resource identifier ending with "site/subdir/"
    And the corpus does not contain a crawled item with source uniform resource identifier ending with "outside.html"

  Scenario: Crawl respects corpus ignore rules
    Given I initialized a corpus at "corpus"
    And a file "corpus/.biblicusignore" exists with contents:
      """
      page.html
      """
    And a hypertext transfer protocol server is serving the workdir
    And a file "site/index.html" exists with contents:
      """
      <html>
        <body>
          <a href="page.html">Page</a>
        </body>
      </html>
      """
    And a file "site/page.html" exists with contents:
      """
      <html><body>ignored</body></html>
      """
    When I crawl the hypertext transfer protocol uniform resource locator "site/index.html" with allowed prefix "site/" into corpus "corpus"
    Then the crawl reports stored_items 1
    And the crawl reports skipped_ignored_items 1
    And the corpus does not contain a crawled item with source uniform resource identifier ending with "site/page.html"

  Scenario: Crawl records errors for missing resources within the prefix
    Given I initialized a corpus at "corpus"
    And a hypertext transfer protocol server is serving the workdir
    And a file "site/index.html" exists with contents:
      """
      <html>
        <body>
          <a href="missing.html#fragment">Missing</a>
        </body>
      </html>
      """
    When I crawl the hypertext transfer protocol uniform resource locator "site/index.html" with allowed prefix "site/" into corpus "corpus"
    Then the crawl reports stored_items 1
    And the crawl reports errored_items 1
