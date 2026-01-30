Feature: Context pack policies
  Context pack policies control evidence ordering, metadata inclusion, and budgets.

  Scenario: Score ordering sorts evidence by score
    Given a retrieval result exists with scored evidence:
      | score | text  |
      | 1.0   | beta  |
      | 5.0   | alpha |
    When I build a context pack from that retrieval result with policy:
      | key              | value |
      | join_with        | \n\n |
      | ordering         | score |
      | include_metadata | false |
    Then the context pack text equals:
      """
      alpha

      beta
      """

  Scenario: Source ordering groups evidence by source
    Given a retrieval result exists with sourced evidence:
      | source_uri | score | text  |
      | source-b   | 1.0   | beta  |
      | source-a   | 2.0   | alpha |
      | source-a   | 1.0   | delta |
    When I build a context pack from that retrieval result with policy:
      | key              | value |
      | join_with        | \n\n |
      | ordering         | source |
      | include_metadata | false |
    Then the context pack text equals:
      """
      alpha

      delta

      beta
      """

  Scenario: Metadata inclusion prepends block metadata
    Given a retrieval result exists with sourced evidence:
      | source_uri | score | text  |
      | source-a   | 10.0  | alpha |
    When I build a context pack from that retrieval result with policy:
      | key              | value |
      | join_with        | \n\n |
      | ordering         | rank |
      | include_metadata | true |
    Then the context pack text equals:
      """
      item_id: item-1
      source_uri: source-a
      score: 10.0
      stage: scan
      alpha
      """

  Scenario: Character budgets drop trailing blocks
    Given a retrieval result exists with evidence text:
      | text |
      | alpha |
      | beta |
    When I build a context pack from that retrieval result with policy:
      | key              | value |
      | join_with        | \n\n |
      | ordering         | rank |
      | include_metadata | false |
    And I fit the context pack to a character budget of 6 characters
    Then the context pack text equals:
      """
      alpha
      """

  Scenario: Character budgets can produce empty context packs
    Given a retrieval result exists with evidence text:
      | text |
      | alpha |
    When I build a context pack from that retrieval result with policy:
      | key              | value |
      | join_with        | \n\n |
      | ordering         | rank |
      | include_metadata | false |
    And I fit the context pack to a character budget of 1 characters
    Then the context pack text is empty

  Scenario: Unknown ordering raises a policy error
    Given a retrieval result exists with evidence text:
      | text |
      | alpha |
    When I attempt to build a context pack with invalid ordering "mystery"
    Then the context pack ordering error mentions "Unknown context pack ordering"
