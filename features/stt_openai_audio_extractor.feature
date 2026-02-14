Feature: OpenAI GPT-4o Audio speech to text extraction
  Audio items can produce derived text artifacts through GPT-4o Audio STT extractor.
  The raw audio bytes remain unchanged in the corpus root.
  GPT-4o Audio uses multimodal understanding, different from Whisper API.

  Scenario: OpenAI Audio extractor requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the OpenAI dependency is unavailable
    And an OpenAI API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-openai-audio" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[openai]"

  Scenario: OpenAI Audio extractor requires an API key
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-openai-audio" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "OPENAI_API_KEY"

  Scenario: OpenAI Audio extractor skips non-audio items
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And an OpenAI API key is configured for this scenario
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "stt-openai-audio" extraction snapshot in corpus "corpus"
    Then the extraction snapshot does not include extracted text for the last ingested item

  Scenario: OpenAI Audio extractor produces transcript for a WAV audio item
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns chat completion "Hello from GPT-4o Audio" for any prompt
    And an OpenAI API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-openai-audio" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "Hello from GPT-4o Audio"
    And the extraction snapshot item provenance uses extractor "stt-openai-audio"

  Scenario: OpenAI Audio extractor handles MP3 audio format
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns chat completion "MP3 test" for any prompt
    And an OpenAI API key is configured for this scenario
    And a file "clip.mp3" exists with bytes:
      """
      ID3
      """
    When I ingest the file "clip.mp3" into corpus "corpus"
    And I build a "stt-openai-audio" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "MP3 test"

  Scenario: OpenAI Audio extractor uses configured custom prompt
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns chat completion "Transcribed with custom prompt" for any prompt
    And an OpenAI API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json                                                                       |
      | stt-openai-audio  | {"prompt":"Transcribe this audio with technical accuracy."}                      |
    Then the extracted text for the last ingested item equals "Transcribed with custom prompt"

  Scenario: OpenAI Audio extractor uses configured model
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns chat completion "Custom model test" for any prompt
    And an OpenAI API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id      | config_json                               |
      | stt-openai-audio  | {"model":"gpt-4o-audio-preview-2024"}    |
    Then the extracted text for the last ingested item equals "Custom model test"
