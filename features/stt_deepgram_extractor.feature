Feature: Deepgram speech to text extraction
  Audio items can produce derived text artifacts through a Deepgram speech to text extractor plugin.
  The raw audio bytes remain unchanged in the corpus raw directory.

  Scenario: Deepgram speech to text extractor requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the Deepgram dependency is unavailable
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-deepgram" extraction run in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[deepgram]"

  Scenario: Deepgram speech to text extractor skips non-audio items
    Given I initialized a corpus at "corpus"
    And a fake Deepgram library is available
    And a Deepgram API key is configured for this scenario
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "stt-deepgram" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: Deepgram speech to text extractor requires a Deepgram API key
    Given I initialized a corpus at "corpus"
    And a fake Deepgram library is available
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-deepgram" extraction run in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "DEEPGRAM_API_KEY"
    And standard error includes "config.yml"

  Scenario: Deepgram speech to text extractor produces transcript for an audio item
    Given I initialized a corpus at "corpus"
    And a fake Deepgram library is available that returns transcript "Hello from Deepgram" for filename "clip.wav"
    And a Deepgram API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-deepgram" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "Hello from Deepgram"
    And the extraction run item provenance uses extractor "stt-deepgram"

  Scenario: Deepgram speech to text extractor accepts model configuration
    Given I initialized a corpus at "corpus"
    And a fake Deepgram library is available that returns transcript "Nova-3 transcript" for filename "clip.wav"
    And a Deepgram API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id | config_json                           |
      | stt-deepgram | {"model":"nova-3","language":"en"}    |
    Then the extracted text for the last ingested item equals "Nova-3 transcript"
    And the Deepgram transcription request used model "nova-3"

  Scenario: Deepgram speech to text extractor accepts smart format configuration
    Given I initialized a corpus at "corpus"
    And a fake Deepgram library is available that returns transcript "Formatted transcript" for filename "clip.wav"
    And a Deepgram API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id | config_json                                    |
      | stt-deepgram | {"smart_format":true,"punctuate":true}         |
    Then the extracted text for the last ingested item equals "Formatted transcript"
    And the Deepgram transcription request used smart format true
    And the Deepgram transcription request used punctuate true

  Scenario: Deepgram speech to text extractor rejects extraction without an API key at runtime
    When I call the Deepgram speech to text extractor without an API key
    Then a fatal extraction error is raised

  Scenario: Deepgram speech to text extractor rejects extraction at runtime when optional dependency is missing
    Given the Deepgram dependency is unavailable
    And a Deepgram API key is configured for this scenario
    When I call the Deepgram speech to text extractor with an API key
    Then a fatal extraction error is raised

  Scenario: Deepgram speech to text output can override earlier metadata output in a pipeline
    Given I initialized a corpus at "corpus"
    And a fake Deepgram library is available that returns transcript "Deepgram transcript wins" for filename "clip.wav"
    And a Deepgram API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" with tags "audio,example" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id   | config_json |
      | metadata-text  | {}          |
      | stt-deepgram   | {}          |
    Then the extracted text for the last ingested item equals "Deepgram transcript wins"
    And the extraction run item provenance uses extractor "stt-deepgram"

  Scenario: Deepgram speech to text returns empty when response has no results
    Given I initialized a corpus at "corpus"
    And a fake Deepgram library is available that returns empty results for filename "clip.wav"
    And a Deepgram API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-deepgram" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item is empty

  Scenario: Deepgram speech to text returns empty when response has empty channels
    Given I initialized a corpus at "corpus"
    And a fake Deepgram library is available that returns empty channels for filename "clip.wav"
    And a Deepgram API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-deepgram" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item is empty

  Scenario: Deepgram speech to text returns empty when response has empty alternatives
    Given I initialized a corpus at "corpus"
    And a fake Deepgram library is available that returns empty alternatives for filename "clip.wav"
    And a Deepgram API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-deepgram" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item is empty
