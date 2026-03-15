Feature: Pipeline recipes
  Pipeline recipes run extraction, retrieval, and analysis for a corpus or collection selector.

  Scenario: Pipeline recipe targets a corpus selector in a collection
    Given a collection "nexus" exists with corpora:
      | name     |
      | catalyst |
      | acme     |
    And a pipeline recipe exists at "pipelines/catalyst.yml" targeting collection "nexus" selector "catalyst*"
    When I run the pipeline recipe "pipelines/catalyst.yml"
    Then the extraction snapshot for corpus "corpora/nexus/catalyst" is built
    And the retrieval snapshot for corpus "corpora/nexus/catalyst" is built

  Scenario: Pipeline recipe runs analysis steps
    Given I initialized a corpus at "corpora/nexus/catalyst"
    And a pipeline recipe exists at "pipelines/catalyst.yml" with analysis steps
    When I run the pipeline recipe "pipelines/catalyst.yml"
    Then the profiling analysis output exists for corpus "corpora/nexus/catalyst"
