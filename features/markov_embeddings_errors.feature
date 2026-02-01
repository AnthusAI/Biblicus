Feature: Markov embeddings error handling
  Markov analysis observation encoding validates embeddings behavior with explicit errors.

  Scenario: Embeddings reject sequences that only contain boundary markers
    When I attempt to build markov observations with embeddings for segments "START,END"
    Then a ValueError is raised
    And the ValueError message includes "Embeddings require at least one non-boundary segment"

  Scenario: Embeddings reject unexpected vector counts from the provider
    When I attempt to build markov observations with embeddings for segments "Alpha" returning 0 vectors
    Then a ValueError is raised
    And the ValueError message includes "unexpected vector count"

