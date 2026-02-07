@integration @audio @deepgram
Feature: Deepgram audio transcription integration
  Audio transcription should work end-to-end against a real corpus and Deepgram.

  Scenario: Deepgram transcribes speech audio
    When I download an audio corpus into "corpus"
    And a Deepgram API key is configured for this scenario
    And I build a "stt-deepgram" extraction snapshot in corpus "corpus"
    Then the extracted text for the item tagged "speech" is not empty in the latest extraction snapshot
