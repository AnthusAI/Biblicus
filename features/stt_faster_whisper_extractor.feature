Feature: Faster-Whisper speech to text extraction
  Audio items can produce derived text artifacts through Faster-Whisper STT extractor.
  The raw audio bytes remain unchanged in the corpus root.
  Faster-Whisper runs Whisper models locally without API costs.

  Scenario: Faster-Whisper extractor requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the faster-whisper dependency is unavailable
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-faster-whisper" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[faster-whisper]"

  Scenario: Faster-Whisper extractor skips non-audio items
    Given I initialized a corpus at "corpus"
    And a fake faster-whisper library is available
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "stt-faster-whisper" extraction snapshot in corpus "corpus"
    Then the extraction snapshot does not include extracted text for the last ingested item

  Scenario: Faster-Whisper extractor produces transcript for an audio item
    Given I initialized a corpus at "corpus"
    And a fake faster-whisper library is available that returns transcript "Hello from Faster Whisper" for filename "clip.wav"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-faster-whisper" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "Hello from Faster Whisper"
    And the extraction snapshot item provenance uses extractor "stt-faster-whisper"

  Scenario: Faster-Whisper uses default large-v3 model
    Given I initialized a corpus at "corpus"
    And a fake faster-whisper library is available that returns transcript "Test text" for filename "clip.wav"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-faster-whisper" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "Test text"
    And the faster-whisper model used model size "large-v3"

  Scenario: Faster-Whisper uses configured model size
    Given I initialized a corpus at "corpus"
    And a fake faster-whisper library is available that returns transcript "Small model" for filename "clip.wav"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id        | config_json                    |
      | stt-faster-whisper  | {"model_size":"small"}        |
    Then the extracted text for the last ingested item equals "Small model"
    And the faster-whisper model used model size "small"

  Scenario: Faster-Whisper uses configured language for better accuracy
    Given I initialized a corpus at "corpus"
    And a fake faster-whisper library is available that returns transcript "Bonjour" with detected language "fr" for file "clip.wav"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id        | config_json                    |
      | stt-faster-whisper  | {"language":"fr"}             |
    Then the extracted text for the last ingested item equals "Bonjour"
    And the faster-whisper transcription used language "fr"

  Scenario: Faster-Whisper uses configured beam size
    Given I initialized a corpus at "corpus"
    And a fake faster-whisper library is available that returns transcript "Beam search test" for filename "clip.wav"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id        | config_json                    |
      | stt-faster-whisper  | {"beam_size":8}               |
    Then the extracted text for the last ingested item equals "Beam search test"
    And the faster-whisper transcription used beam size 8

  Scenario: Faster-Whisper handles FLAC audio format
    Given I initialized a corpus at "corpus"
    And a fake faster-whisper library is available that returns transcript "FLAC format test" for filename "clip.flac"
    And a file "clip.flac" exists with bytes:
      """
      fLaC\x00\x00\x00\x22
      """
    When I ingest the file "clip.flac" into corpus "corpus"
    And I build a "stt-faster-whisper" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "FLAC format test"
