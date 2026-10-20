Feature: URL source classification
  Biblicus should treat a source URL as YouTube only when its host is youtube.com, a
  subdomain of youtube.com, or youtu.be, never because those words appear elsewhere in the
  URL or in a lookalike host.

  Scenario Outline: Genuine YouTube hosts are extracted as YouTube
    When I classify the source URL "<uri>" using a fake YouTube converter
    Then the URL text source kind is "youtube"
    And the fake YouTube converter received "https://www.youtube.com/watch?v=abc123"

    Examples:
      | uri                                    |
      | https://www.youtube.com/watch?v=abc123 |
      | https://youtube.com/watch?v=abc123     |
      | https://m.youtube.com/watch?v=abc123   |
      | https://YouTube.com:443/shorts/abc123  |
      | https://youtu.be/abc123                |

  Scenario Outline: Lookalike hosts are not treated as YouTube
    When I classify the source URL "<uri>" using a fake YouTube converter
    Then the URL text source kind is "web"
    And the URL text strategy is "markdown-then-html-then-direct"

    Examples:
      | uri                                        |
      | https://notyoutube.com/watch?v=x           |
      | https://youtube.com.evil.example/watch?v=x |
      | https://evil.example/?u=youtube.com        |
      | https://evil.example/watch?v=x#youtu.be    |
      | https://notyoutu.be/abc123                 |
