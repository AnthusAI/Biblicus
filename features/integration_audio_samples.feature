@integration
Feature: Audio corpus integration
  A corpus can ingest audio items from remote sources and record them with the correct media type.

  Scenario: Download audio and extract metadata text for retrieval baselines
    When I download an audio corpus into "corpus"
    Then the corpus contains at least 1 item with media type "audio/ogg"
    And the corpus contains at least 1 item with media type "audio/wav"
    And the corpus contains at least 1 item tagged "no-speech"
    When I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id   | config_json |
      | metadata-text  | {}          |
    Then the extracted text for the item tagged "audio" is not empty in the latest extraction run
