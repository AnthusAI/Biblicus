Feature: Typed entity and relation extraction
  A publication defines a closed vocabulary of entity kinds and relation types. Biblicus extracts entities and relations of those kinds from the extracted text of corpus items, resolves mentions of accepted entities by exact alias match, and proposes everything else for the desk to review.

  Background:
    Given I initialized a corpus at "typed-lab"
    And a file "vocabulary.yml" exists with contents:
      """
      version: 1
      publication: lab
      entity_kinds:
        - key: maker
          label: company or developer
        - key: model
          label: AI model
        - key: licence
          label: software licence
      relation_types:
        - key: made_by
          label: made by
        - key: licensed_under
          label: licensed under
      """
    And a file "registry.json" exists with contents:
      """
      [
        {"key": "name-a", "kind": "maker", "aliases": ["NAME-A"]},
        {"key": "gemma-3", "kind": "model", "aliases": ["Gemma 3"]},
        {"key": "apache-2", "kind": "licence", "aliases": ["Apache 2.0", "Apache-2"]}
      ]
      """
    And a fake GLiNER2 library finds these entities:
      | text          | label                | score |
      | NAME-A        | company or developer | 0.9   |
      | Gemma 3       | company or developer | 0.9   |
      | Guard 1.1     | company or developer | 0.6   |
      | Guard 1.1     | AI model             | 0.95  |
      | Gemma 3       | AI model             | 0.7   |
      | Gemma-3-4B-it | AI model             | 0.9   |
      | Apache 2.0    | software licence     | 0.8   |
      | Lowscore      | AI model             | 0.5   |
    And a fake GLiNER2 library finds these relations:
      | subject   | label          | object     | score |
      | Guard 1.1 | made by        | NAME-A     | 0.9   |
      | Guard 1.1 | made by        | NAME-A     | 0.8   |
      | Guard 1.1 | licensed under | Apache 2.0 | 0.75  |
      | Guard 1.1 | licensed under | Apache 2.0 | 0.85  |
      | Gemma 3   | made by        | NAME-A     | 0.9   |
      | Guard 1.1 | made by        | Guard 1.1  | 0.9   |
      | Guard 1.1 | made by        | released   | 0.9   |
    And the corpus "typed-lab" has an item "alpha" with text:
      """
      NAME-A released Guard 1.1 under Apache 2.0.
      """

  Scenario: Closed vocabulary
    Given the corpus "typed-lab" has an item "beta" with text:
      """
      Gemma 3 is made by NAME-A.
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json"
    Then the standard output validates against the published "extract-typed-entities" response schema
    And every entity kind and relation type in the output belongs to the vocabulary
    And item "alpha" has these entities:
      | text       | kind    | state    | entity_key |
      | NAME-A     | maker   | resolved | name-a     |
      | Guard 1.1  | model   | proposed | -          |
      | Apache 2.0 | licence | resolved | apache-2   |
    And item "alpha" has these relations:
      | type           | subject   | object     | state    |
      | made_by        | Guard 1.1 | NAME-A     | proposed |
      | licensed_under | Guard 1.1 | Apache 2.0 | proposed |
    And the output names backend "gliner2" with threshold 0.7 and vocabulary "lab" version 1

  Scenario: A relation is resolved only when both endpoints are resolved
    Given the corpus "typed-lab" has an item "beta" with text:
      """
      Gemma 3 is made by NAME-A.
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json --item-id item:beta"
    Then item "beta" has these entities:
      | text    | kind  | state    | entity_key |
      | Gemma 3 | model | resolved | gemma-3    |
      | NAME-A  | maker | resolved | name-a     |
    And item "beta" has these relations:
      | type    | subject | object | state    |
      | made_by | Gemma 3 | NAME-A | resolved |

  Scenario: Evidence
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json"
    Then every entity and relation of item "alpha" in corpus "typed-lab" carries its item id and offsets into the text
    And the output contains no timestamps

  Scenario: Entity resolution by alias
    Given the corpus "typed-lab" has an item "gamma" with text:
      """
      NAME-A, name-a, Name A, name   a and NAME_A all spell it differently.
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json --item-id item:gamma"
    Then item "gamma" has these entities:
      | text   | kind  | state    | entity_key |
      | NAME-A | maker | resolved | name-a     |
      | name-a | maker | resolved | name-a     |
      | Name A | maker | resolved | name-a     |
      | name   a | maker | resolved | name-a   |
      | NAME_A | maker | resolved | name-a     |
    And the output summary counts 1 items, 5 entities, 5 resolved, 0 proposed and 0 relations

  Scenario: Proposed new entity and no prefix merging
    Given the corpus "typed-lab" has an item "delta" with text:
      """
      Guard 1.1 builds on Gemma-3-4B-it and Gemma 3.
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json --item-id item:delta"
    Then item "delta" has these entities:
      | text          | kind  | state    | entity_key |
      | Guard 1.1     | model | proposed | -          |
      | Gemma-3-4B-it | model | proposed | -          |
      | Gemma 3       | model | resolved | gemma-3    |

  Scenario: A model span that equals an alias resolves, and a span of another kind does not
    Given the corpus "typed-lab" has an item "epsilon" with text:
      """
      Notes on pre-Apache 2.0 terms.
      """
    And the corpus "typed-lab" has an item "zeta" with text:
      """
      Notes on pre-Gemma 3 terms.
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json --item-id item:epsilon --item-id item:zeta"
    Then item "epsilon" has these entities:
      | text       | kind    | state    | entity_key |
      | Apache 2.0 | licence | resolved | apache-2   |
    And item "zeta" has these entities:
      | text    | kind  | state    | entity_key |
      | Gemma 3 | maker | proposed | -          |

  Scenario: Without a registry every mention is proposed
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml"
    Then item "alpha" has these entities:
      | text       | kind    | state    | entity_key |
      | NAME-A     | maker   | proposed | -          |
      | Guard 1.1  | model   | proposed | -          |
      | Apache 2.0 | licence | proposed | -          |

  Scenario: An entity may repeat its own alias
    Given a file "repeated-registry.json" exists with contents:
      """
      [{"key": "name-a", "kind": "maker", "aliases": ["NAME-A", "name a"]}]
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry repeated-registry.json --backend registry-only"
    Then item "alpha" has these entities:
      | text   | kind  | state    | entity_key |
      | NAME-A | maker | resolved | name-a     |

  Scenario: A registry entity without aliases resolves nothing
    Given a file "bare-registry.json" exists with contents:
      """
      [{"key": "name-a", "kind": "maker"}]
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry bare-registry.json"
    Then the output summary counts 1 items, 3 entities, 0 resolved, 3 proposed and 2 relations

  Scenario: The registry-only backend resolves registry entities and proposes nothing
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json --backend registry-only"
    Then item "alpha" has these entities:
      | text       | kind    | state    | entity_key |
      | NAME-A     | maker   | resolved | name-a     |
      | Apache 2.0 | licence | resolved | apache-2   |
    And item "alpha" has these relations:
      | type | subject | object | state |
    And the output names backend "registry-only" with threshold 0.7 and vocabulary "lab" version 1
    And the output names no model and no revision
    And the fake GLiNER2 library read no windows

  Scenario: The pinned model is loaded once at its pinned revision
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json"
    Then the output names model "fastino/gliner2-base-v1" at revision "f9634218e53580c56edf0de97ca1a7d3f1c2354e"
    And the fake GLiNER2 library loaded model fastino/gliner2-base-v1 at revision f9634218e53580c56edf0de97ca1a7d3f1c2354e 1 time

  Scenario: Deterministic and cached
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json"
    Then the run metadata of corpus "typed-lab" reports 1 backend calls and 0 cache hits
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json" a second time
    Then both runs print identical standard output
    And the run metadata of corpus "typed-lab" reports 0 backend calls and 1 cache hits
    And the corpus "typed-lab" has 1 typed-entities runs
    And the fake GLiNER2 library read 1 windows
    And the fake GLiNER2 library loaded model fastino/gliner2-base-v1 at revision f9634218e53580c56edf0de97ca1a7d3f1c2354e 1 time

  Scenario: A different threshold is a different cache entry
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json"
    And I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json --threshold 0.4"
    Then the run metadata of corpus "typed-lab" reports 1 backend calls and 0 cache hits
    And the corpus "typed-lab" has 2 typed-entities runs

  Scenario: A changed registry changes the resolution but not the cached model output
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json"
    And I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml"
    Then the run metadata of corpus "typed-lab" reports 0 backend calls and 1 cache hits
    And the output summary counts 1 items, 3 entities, 0 resolved, 3 proposed and 2 relations

  Scenario: A changed vocabulary is a different cache entry
    Given a file "other-vocabulary.yml" exists with contents:
      """
      version: 2
      publication: lab
      entity_kinds:
        - key: maker
          label: company or developer
        - key: model
          label: AI model
        - key: licence
          label: software licence
      relation_types:
        - key: made_by
          label: made by
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml"
    And I extract typed entities in corpus "typed-lab" with options "--vocabulary other-vocabulary.yml"
    Then the run metadata of corpus "typed-lab" reports 1 backend calls and 0 cache hits
    And the output names backend "gliner2" with threshold 0.7 and vocabulary "lab" version 2

  Scenario: Items are chosen by identifier and the output is also written to a directory
    Given the corpus "typed-lab" has an item "beta" with text:
      """
      Gemma 3 is made by NAME-A.
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json --item-id item:beta --item-id item:alpha --out delivered --extraction-snapshot snapshot:latest"
    Then the output summary counts 2 items, 5 entities, 4 resolved, 1 proposed and 3 relations
    And the file "delivered/output.json" matches the standard output
    And the corpus "typed-lab" stores the output under its typed-entities analysis folder

  Scenario: Text is read in paragraph windows and offsets stay relative to the item
    Given a fake GLiNER2 library finds these entities:
      | text    | label    | score |
      | Guard 2 | AI model | 0.95  |
      | Guard 2.| AI model | 0.9   |
      | ...     | AI model | 0.9   |
    And a fake GLiNER2 library finds these relations:
      | subject | label   | object  | score |
      | ...     | made by | Guard 2 | 0.9   |
    And the corpus "typed-lab" has an item "gaps" with escaped text "Guard 2 first... done\n\n \t \n\nThen Guard 2. again."
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --item-id item:gaps"
    Then the fake GLiNER2 library read 2 windows
    And item "gaps" has these entities:
      | text    | kind  | state    | entity_key |
      | Guard 2 | model | proposed | -          |
      | Guard 2 | model | proposed | -          |
    And every entity text in the output appears at its offsets in item "gaps" of corpus "typed-lab"

  Scenario: Long paragraphs are cut at whitespace and unbroken runs at the limit
    Given the corpus "typed-lab" has an item "long" of 1 paragraphs of 700 words
    And the corpus "typed-lab" has an item "unbroken" of one unbroken run of 4500 characters
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --item-id item:long --item-id item:unbroken"
    Then the fake GLiNER2 library read 6 windows
    And no fake GLiNER2 window is longer than 2000 characters
    And item "unbroken" has no entities and no relations

  Scenario: A vocabulary without relation types extracts entities only
    Given a file "entities-only.yml" exists with contents:
      """
      version: 1
      publication: lab
      entity_kinds:
        - key: model
          label: AI model
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary entities-only.yml"
    Then item "alpha" has these entities:
      | text      | kind  | state    | entity_key |
      | Guard 1.1 | model | proposed | -          |
    And item "alpha" has these relations:
      | type | subject | object | state |

  Scenario: Alias normalisation ignores case, spacing and punctuation
    Then normalising "NAME-A" and "name a" gives the same alias
    And normalising "Qwen3.5-4B" and "qwen3 5   4b" gives the same alias

  Scenario: The model dependency is an optional extra
    Given the GLiNER2 dependency is not installed
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml"
    Then standard output is one failure envelope with code "operation_failed"
    And the failure envelope message includes "biblicus[typed-extraction]"

  Scenario: A run served entirely from the cache needs no model
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml"
    And the GLiNER2 dependency is not installed
    And I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml" a second time
    Then both runs print identical standard output

  Scenario: An item without extracted text is reported
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --item-id missing-item"
    Then standard output is one failure envelope with code "operation_failed"
    And the failure envelope message includes "Item missing-item has no extracted text"

  Scenario: A corpus without an extraction snapshot is reported
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml"
    Then standard output is one failure envelope with code "operation_failed"
    And the failure envelope message includes "no extraction snapshot"

  Scenario: An out of range threshold is rejected before any work
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --threshold 1.5"
    Then standard output is one failure envelope with code "invalid_request"
    And the failure envelope message includes "threshold"

  Scenario: A missing vocabulary file is reported
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary absent.yml"
    Then standard output is one failure envelope with code "operation_failed"
    And the failure envelope message includes "Vocabulary file not found"

  Scenario: A missing registry file is reported
    Given I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry absent.json"
    Then standard output is one failure envelope with code "operation_failed"
    And the failure envelope message includes "Registry file not found"

  Scenario Outline: An invalid vocabulary is reported
    Given a file "bad-vocabulary.yml" exists with contents:
      """
      <content>
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary bad-vocabulary.yml"
    Then standard output is one failure envelope with code "operation_failed"
    And the failure envelope message includes "<message>"

    Examples:
      | content                                                                                                                         | message                       |
      | entity_kinds: [unclosed                                                                                                         | is not valid YAML             |
      | [1, 2]                                                                                                                          | must contain a mapping        |
      | {"version": 1, "publication": "lab", "entity_kinds": []}                                                                       | Invalid vocabulary            |
      | {"version": 1, "publication": "lab", "entity_kinds": [{"key": "a", "label": "A"}, {"key": "a", "label": "B"}]}                 | Duplicate entity kind key: a  |
      | {"version": 1, "publication": "lab", "entity_kinds": [{"key": "a", "label": "A"}, {"key": "b", "label": "A"}]}                 | Duplicate entity kind label: A |

  Scenario Outline: An invalid registry is reported
    Given a file "bad-registry.json" exists with contents:
      """
      <content>
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry bad-registry.json"
    Then standard output is one failure envelope with code "operation_failed"
    And the failure envelope message includes "<message>"

    Examples:
      | content                                                                                                                    | message                         |
      | [{"key": "a"                                                                                                               | is not valid JSON               |
      | {"key": "a"}                                                                                                               | must contain a JSON list        |
      | [{"kind": "maker"}]                                                                                                        | Invalid registry                |
      | [{"key": "a", "kind": "unknown", "aliases": ["A"]}]                                                                        | outside the vocabulary          |
      | [{"key": "a", "kind": "maker", "aliases": ["  -- "]}]                                                                      | has an empty alias              |
      | [{"key": "a", "kind": "maker", "aliases": ["Same"]}, {"key": "b", "kind": "maker", "aliases": ["same"]}]                   | belongs to both a and b         |

  Scenario: Output models reject inconsistent entities
    Then an entity that is resolved without an entity key is rejected
    And a span that ends before it starts is rejected
