Feature: Speech to text extraction
  Audio items can produce derived text artifacts through a speech to text extractor plugin.
  The raw audio bytes remain unchanged in the corpus raw directory.

  Scenario: Speech to text extractor requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the OpenAI dependency is unavailable
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-openai" extraction run in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[openai]"

  Scenario: Speech to text extractor skips non-audio items
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And an OpenAI API key is configured for this scenario
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "stt-openai" extraction run in corpus "corpus"
    Then the extraction run does not include extracted text for the last ingested item

  Scenario: Speech to text extractor requires an OpenAI API key
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-openai" extraction run in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "OPENAI_API_KEY"
    And standard error includes "config.yml"

  Scenario: Speech to text extractor produces transcript for an audio item
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns transcript "Hello from speech to text" for filename "clip.wav"
    And an OpenAI API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-openai" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "Hello from speech to text"
    And the extraction run item provenance uses extractor "stt-openai"

  Scenario: Speech to text suppresses no-speech audio when probability is high
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns verbose transcript "Hallucinated text" for filename "clip.wav" with segments:
      """
      ["not-a-dict", {"no_speech_prob": "high"}, {"no_speech_prob": 0.99}]
      """
    And an OpenAI API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id | config_json                                                        |
      | stt-openai   | {"response_format":"verbose_json","no_speech_probability_threshold":0.9} |
    Then the extracted text for the last ingested item is empty
    And the OpenAI transcription request used response format "verbose_json"
    And the extraction run item provenance uses extractor "stt-openai"

  Scenario: No-speech suppression requires verbose response format
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available
    And an OpenAI API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id | config_json                                  |
      | stt-openai   | {"no_speech_probability_threshold":0.9}      |
    Then the command fails with exit code 2
    And standard error includes "no_speech_probability_threshold requires response_format"

  Scenario: Speech to text keeps transcript when no-speech probability is low
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns verbose transcript "Real words" for filename "clip.wav" with segments:
      """
      [{"no_speech_prob": 0.1}]
      """
    And an OpenAI API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id | config_json                                                        |
      | stt-openai   | {"response_format":"verbose_json","no_speech_probability_threshold":0.9} |
    Then the extracted text for the last ingested item equals "Real words"

  Scenario: Speech to text extractor accepts dict transcription results
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns a dict transcript "Hello from dict result" for filename "clip.wav"
    And an OpenAI API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-openai" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "Hello from dict result"
    And the extraction run item provenance uses extractor "stt-openai"

  Scenario: Speech to text extractor rejects extraction without an API key at runtime
    When I call the speech to text extractor without an API key
    Then a fatal extraction error is raised

  Scenario: Speech to text extractor rejects extraction at runtime when optional dependency is missing
    Given the OpenAI dependency is unavailable
    And an OpenAI API key is configured for this scenario
    When I call the speech to text extractor with an API key
    Then a fatal extraction error is raised

  Scenario: Speech to text output can override earlier metadata output in a pipeline
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns transcript "Transcript wins" for filename "clip.wav"
    And an OpenAI API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" with tags "audio,example" into corpus "corpus"
    And I build a "pipeline" extraction run in corpus "corpus" with steps:
      | extractor_id   | config_json |
      | metadata-text  | {}          |
      | stt-openai     | {}          |
    Then the extracted text for the last ingested item equals "Transcript wins"
    And the extraction run item provenance uses extractor "stt-openai"
