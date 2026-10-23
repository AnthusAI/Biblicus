@integration @typed_extraction
Feature: Typed extraction with the pinned GLiNER2 model
  The default backend runs the pinned GLiNER2 checkpoint. This integration runs only when the typed-extraction extra is installed and the checkpoint is already in the local Hugging Face cache; it never downloads a model.

  Scenario: The pinned model extracts entities from a corpus item and the second run is served from the cache
    Given the pinned GLiNER2 model is cached locally
    And I initialized a corpus at "typed-real"
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
    And the corpus "typed-real" has an item "release" with text:
      """
      AccuKnox Inc. releases Guard 1.1, an Apache-2.0 guardrail model fine-tuned from Qwen3.5-4B.
      """
    And I built a pass-through extraction snapshot in corpus "typed-real"
    When I extract typed entities in corpus "typed-real" with options "--vocabulary vocabulary.yml"
    Then the standard output validates against the published "extract-typed-entities" response schema
    And the output has at least 2 entities
    And every entity kind and relation type in the output belongs to the vocabulary
    And every entity text in the output appears at its offsets in item "release" of corpus "typed-real"
    And the output names model "fastino/gliner2-base-v1" at revision "f9634218e53580c56edf0de97ca1a7d3f1c2354e"
    When I extract typed entities in corpus "typed-real" with options "--vocabulary vocabulary.yml" a second time
    Then both runs print identical standard output
    And the run metadata of corpus "typed-real" reports 0 backend calls and 1 cache hits
