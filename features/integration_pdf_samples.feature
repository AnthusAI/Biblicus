@integration
Feature: Portable Document Format integration corpus
  The integration corpus downloads public Portable Document Format files into a local corpus.

  Scenario: Download and ingest a small Portable Document Format corpus
    When I download a Portable Document Format corpus into "corpus"
    Then the corpus contains at least 2 items

