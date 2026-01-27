@integration
Feature: Wikipedia integration corpus
  The integration corpus downloads public Wikipedia pages into a local corpus.

  Scenario: Download and ingest a small Wikipedia corpus
    When I download a Wikipedia corpus into "corpus"
    Then the corpus contains at least 5 items
