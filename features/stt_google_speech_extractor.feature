Feature: Google Speech speech to text extraction
  Audio items can produce derived text artifacts through Google Speech STT extractor.
  The raw audio bytes remain unchanged in the corpus root.

  Scenario: Google Speech extractor requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the Google Speech dependency is unavailable
    And a Google Cloud credentials file is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-google-speech" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[google]"

  Scenario: Google Speech extractor requires credentials
    Given I initialized a corpus at "corpus"
    And a fake Google Speech library is available
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-google-speech" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "GOOGLE_APPLICATION_CREDENTIALS"

  Scenario: Google Speech extractor skips non-audio items
    Given I initialized a corpus at "corpus"
    And a fake Google Speech library is available
    And a Google Cloud credentials file is configured for this scenario
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "stt-google-speech" extraction snapshot in corpus "corpus"
    Then the extraction snapshot does not include extracted text for the last ingested item

  Scenario: Google Speech extractor produces transcript for an audio item
    Given I initialized a corpus at "corpus"
    And a fake Google Speech library is available that returns transcript "Hello from Google Speech" for filename "clip.wav"
    And a Google Cloud credentials file is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-google-speech" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "Hello from Google Speech"
    And the extraction snapshot item provenance uses extractor "stt-google-speech"

  Scenario: Google Speech uses configured language and model
    Given I initialized a corpus at "corpus"
    And a fake Google Speech library is available that returns transcript "Bonjour" for filename "clip.wav"
    And a Google Cloud credentials file is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json                                              |
      | stt-google-speech  | {"language_code":"fr-FR","model":"latest_long"}         |
    Then the extracted text for the last ingested item equals "Bonjour"
    And the Google Speech request used language code "fr-FR"
    And the Google Speech request used model "latest_long"

  Scenario: Google Speech enables automatic punctuation by default
    Given I initialized a corpus at "corpus"
    And a fake Google Speech library is available that returns transcript "Hello. This is a test." for filename "clip.wav"
    And a Google Cloud credentials file is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-google-speech" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "Hello. This is a test."
    And the Google Speech request enabled automatic punctuation

  Scenario: Google Speech enables speaker diarization when configured
    Given I initialized a corpus at "corpus"
    And a fake Google Speech library is available that returns transcript "Speaker one. Speaker two." for filename "clip.wav"
    And a Google Cloud credentials file is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json                                                                  |
      | stt-google-speech  | {"enable_speaker_diarization":true,"diarization_speaker_count":2}           |
    Then the extracted text for the last ingested item equals "Speaker one. Speaker two."
    And the Google Speech request enabled speaker diarization

  Scenario: Google Speech handles FLAC audio format
    Given I initialized a corpus at "corpus"
    And a fake Google Speech library is available that returns transcript "FLAC test" for filename "clip.flac"
    And a Google Cloud credentials file is configured for this scenario
    And a file "clip.flac" exists with bytes:
      """
      fLaC\x00\x00\x00\x22
      """
    When I ingest the file "clip.flac" into corpus "corpus"
    And I build a "stt-google-speech" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "FLAC test"
