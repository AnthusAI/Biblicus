@integration @openai @audio
Feature: Audio transcription integration
  Audio transcription should work end-to-end against a real corpus and OpenAI.

  Scenario: OpenAI transcribes speech audio
    Given an OpenAI API key is configured for this scenario
    When I download an audio corpus into "corpus"
    And I build a "stt-openai" extraction snapshot in corpus "corpus"
    Then the extracted text for the item tagged "speech" is not empty in the latest extraction snapshot
