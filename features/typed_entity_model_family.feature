Feature: A model is its own entity kind and joins its model family only when the text says so
  The vocabulary a publication supplies can hold both a "model" kind (a specific named model
  such as a checkpoint with a size suffix) and a "model_family" kind (the line of models above
  it). The extractor keeps them apart. It relates a model to its family with the "member_of"
  relation only when the text states the membership, and it never infers a family from a
  shared name.

  Background:
    Given I initialized a corpus at "typed-lab"
    And a file "vocabulary.yml" exists with contents:
      """
      version: 1
      publication: lab
      entity_kinds:
        - key: model
          label: AI model
        - key: model_family
          label: model family
      relation_types:
        - key: member_of
          label: member of
        - key: successor_of
          label: successor of
      """
    And a fake GLiNER2 library finds these entities:
      | text        | label        | score |
      | Kestrel 9B  | AI model     | 0.9   |
      | Kestrel 12B | AI model     | 0.9   |
      | Merlin      | model family | 0.9   |
      | Plover 2    | AI model     | 0.9   |
    And a fake GLiNER2 library finds these relations:
      | subject     | label        | object     | score |
      | Kestrel 9B  | member of    | Merlin     | 0.9   |
      | Kestrel 12B | successor of | Kestrel 9B | 0.9   |
    And the corpus "typed-lab" has an item "alpha" with text:
      """
      Kestrel 9B belongs to the Merlin family. Kestrel 12B is the next version.
      """
    And the corpus "typed-lab" has an item "beta" with text:
      """
      Plover 2 was released last week.
      """
    And I built a pass-through extraction snapshot in corpus "typed-lab"

  Scenario: A model and its family are separate kinds joined by member of
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml"
    Then the standard output validates against the published "extract-typed-entities" response schema
    And item "alpha" has these entities:
      | text        | kind         | state    | entity_key |
      | Kestrel 9B  | model        | proposed | -          |
      | Merlin      | model_family | proposed | -          |
      | Kestrel 12B | model        | proposed | -          |
    And item "alpha" has these relations:
      | type         | subject     | object     | state    |
      | member_of    | Kestrel 9B  | Merlin     | proposed |
      | successor_of | Kestrel 12B | Kestrel 9B | proposed |

  Scenario: A model the text does not place in a family stays unrelated
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml"
    Then item "beta" has these entities:
      | text     | kind  | state    | entity_key |
      | Plover 2 | model | proposed | -          |
    And item "beta" has no relations

  Scenario: Member of resolves when both the model and its family are accepted
    Given a file "registry.json" exists with contents:
      """
      [
        {"key": "kestrel-9b", "kind": "model", "aliases": ["Kestrel 9B"]},
        {"key": "merlin", "kind": "model_family", "aliases": ["Merlin"]}
      ]
      """
    When I extract typed entities in corpus "typed-lab" with options "--vocabulary vocabulary.yml --registry registry.json"
    Then item "alpha" has these relations:
      | type         | subject     | object     | state    |
      | member_of    | Kestrel 9B  | Merlin     | resolved |
      | successor_of | Kestrel 12B | Kestrel 9B | proposed |
