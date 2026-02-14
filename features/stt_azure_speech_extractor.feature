Feature: Azure Speech speech to text extraction
  Audio items can produce derived text artifacts through Azure Speech STT extractor.
  The raw audio bytes remain unchanged in the corpus root.

  Scenario: Azure Speech extractor requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the Azure Speech dependency is unavailable
    And an Azure Speech API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-azure-speech" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[azure]"

  Scenario: Azure Speech extractor requires an API key
    Given I initialized a corpus at "corpus"
    And a fake Azure Speech library is available
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-azure-speech" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "AZURE_SPEECH_KEY"

  Scenario: Azure Speech extractor skips non-audio items
    Given I initialized a corpus at "corpus"
    And a fake Azure Speech library is available
    And an Azure Speech API key is configured for this scenario
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "stt-azure-speech" extraction snapshot in corpus "corpus"
    Then the extraction snapshot does not include extracted text for the last ingested item

  Scenario: Azure Speech extractor produces transcript for an audio item
    Given I initialized a corpus at "corpus"
    And a fake Azure Speech library is available that returns transcript "Hello from Azure Speech" for filename "clip.wav"
    And an Azure Speech API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-azure-speech" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "Hello from Azure Speech"
    And the extraction snapshot item provenance uses extractor "stt-azure-speech"

  Scenario: Azure Speech uses configured region and language
    Given I initialized a corpus at "corpus"
    And a fake Azure Speech library is available that returns transcript "Bonjour" for filename "clip.wav"
    And an Azure Speech API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json                                          |
      | stt-azure-speech  | {"region":"westeurope","language":"fr-FR"}           |
    Then the extracted text for the last ingested item equals "Bonjour"
    And the Azure Speech recognizer used region "westeurope"

  Scenario: Azure Speech handles no speech detected
    Given I initialized a corpus at "corpus"
    And a fake Azure Speech library is available that returns no speech for filename "clip.wav"
    And an Azure Speech API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-azure-speech" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item is empty

  Scenario: Azure Speech handles recognition cancellation
    Given I initialized a corpus at "corpus"
    And a fake Azure Speech library is available that returns cancelled recognition for filename "clip.wav" with reason "InvalidAudioFormat"
    And an Azure Speech API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-azure-speech" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "InvalidAudioFormat"

  Scenario: Azure Speech enables dictation mode when configured
    Given I initialized a corpus at "corpus"
    And a fake Azure Speech library is available that returns transcript "Hello. This is a test." for filename "clip.wav"
    And an Azure Speech API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json                          |
      | stt-azure-speech  | {"enable_dictation":true}            |
    Then the extracted text for the last ingested item equals "Hello. This is a test."
    And the Azure Speech recognizer enabled dictation

  Scenario: Azure Speech masks profanity when configured
    Given I initialized a corpus at "corpus"
    And a fake Azure Speech library is available that returns transcript "Test speech" for filename "clip.wav"
    And an Azure Speech API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json                          |
      | stt-azure-speech  | {"profanity_option":"masked"}       |
    Then the extracted text for the last ingested item equals "Test speech"
    And the Azure Speech recognizer used profanity option "Masked"

  Scenario: Azure Speech removes profanity when configured
    Given I initialized a corpus at "corpus"
    And a fake Azure Speech library is available that returns transcript "Clean text" for filename "clip.wav"
    And an Azure Speech API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json                          |
      | stt-azure-speech  | {"profanity_option":"removed"}      |
    Then the extracted text for the last ingested item equals "Clean text"
    And the Azure Speech recognizer used profanity option "Removed"

  Scenario: Azure Speech uses raw profanity by default
    Given I initialized a corpus at "corpus"
    And a fake Azure Speech library is available that returns transcript "Raw text" for filename "clip.wav"
    And an Azure Speech API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-azure-speech" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "Raw text"
    And the Azure Speech recognizer used profanity option "Raw"
