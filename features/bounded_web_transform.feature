Feature: Bounded web transformation through a trusted host gateway
  Scenario Outline: Transform extracted source without bypassing host admission
    Given a disposable web transformation gateway for "<case>"
    When the bounded web transformation command executes
    Then the web transformation contract for "<case>" holds

    Examples:
      | case                 |
      | article              |
      | title                |
      | subtitle             |
      | summary              |
      | invalid_json         |
      | non_object           |
      | empty_source         |
      | unknown_field        |
      | wrong_type           |
      | wrong_model          |
      | missing_key          |
      | missing_base         |
      | conflicting_base     |
      | non_loopback         |
      | wrong_path           |
      | base_query           |
      | nonzero_retries      |
      | input_bytes          |
      | request_bytes        |
      | denied               |
      | uncertain            |
      | redirect             |
      | transport            |
      | bad_json             |
      | incomplete           |
      | refusal              |
      | wrong_output         |
      | empty_ids            |
      | unknown_ids          |
      | duplicate_ids        |
      | reversed_ids         |
      | boolean_ids          |
      | blank_value          |
      | extra_output         |
      | denied_reduce        |
      | oversize_response    |
      | file_input           |
      | missing_file         |
      | proxy_ignored        |
      | empty_output         |
      | metadata_wrong_model |
      | blank_reduce         |
      | negative_ids         |
      | blank_paragraph      |
      | credentials_in_base  |
      | malformed_base       |
