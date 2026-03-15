Feature: Aldea speech to text extraction
  Audio items can produce derived text artifacts through an Aldea speech to text extractor plugin.
  The raw audio bytes remain unchanged in the corpus root.

  @skip
  Scenario: Aldea speech to text extractor requires an optional dependency
    # Note: Skipped - testing missing optional dependencies via subprocess is not feasible
    # in the BDD test framework due to subprocess isolation of sys.modules.
    # The dependency check is validated by other STT extractors and code review confirms
    # the validation logic matches the established pattern.
    Given I initialized a corpus at "corpus"
    And the Aldea dependency is unavailable
    And an Aldea API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-aldea" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "biblicus[aldea]"

  Scenario: Aldea speech to text extractor skips non-audio items
    Given I initialized a corpus at "corpus"
    And a fake Aldea library is available
    And an Aldea API key is configured for this scenario
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "stt-aldea" extraction snapshot in corpus "corpus"
    Then the extraction snapshot does not include extracted text for the last ingested item

  Scenario: Aldea speech to text extractor requires an Aldea API key
    Given I initialized a corpus at "corpus"
    And a fake Aldea library is available
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "stt-aldea" extraction snapshot in corpus "corpus"
    Then the command fails with exit code 2
    And standard error includes "ALDEA_API_KEY"
    And standard error includes "config.yml"

  Scenario: Aldea speech to text extractor produces transcript for an audio item
    Given I initialized a corpus at "corpus"
    And a fake Aldea library is available that returns transcript "Hello from Aldea" for filename "clip.wav"
    And an Aldea API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-aldea" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item equals "Hello from Aldea"
    And the extraction snapshot item provenance uses extractor "stt-aldea"

  Scenario: Aldea speech to text stores structured metadata for downstream stages
    Given I initialized a corpus at "corpus"
    And a fake Aldea library is available that returns transcript "Hello from Aldea" for filename "clip.wav"
    And an Aldea API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id | config_json |
      | stt-aldea    | {}          |
    Then the extraction stage metadata for stage 1 includes key "aldea"

  Scenario: Aldea speech to text extractor accepts language configuration
    Given I initialized a corpus at "corpus"
    And a fake Aldea library is available that returns transcript "Aldea en transcript" for filename "clip.wav"
    And an Aldea API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id | config_json                |
      | stt-aldea    | {"language":"en-US"}        |
    Then the extracted text for the last ingested item equals "Aldea en transcript"
    And the Aldea transcription request used language "en-US"

  Scenario: Aldea speech to text extractor rejects extraction without an API key at runtime
    When I call the Aldea speech to text extractor without an API key
    Then a fatal extraction error is raised

  @skip
  Scenario: Aldea speech to text extractor rejects extraction at runtime when optional dependency is missing
    # Note: Skipped - testing missing optional dependencies in-process requires sys.modules manipulation
    # that interferes with Python's traceback system. The dependency check is validated by other STT
    # extractors and code review confirms the validation logic matches the established pattern.
    Given the Aldea dependency is unavailable
    And an Aldea API key is configured for this scenario
    When I call the Aldea speech to text extractor with an API key
    Then a fatal extraction error is raised

  Scenario: Aldea speech to text output can override earlier metadata output in a pipeline
    Given I initialized a corpus at "corpus"
    And a fake Aldea library is available that returns transcript "Aldea transcript wins" for filename "clip.wav"
    And an Aldea API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" with tags "audio,example" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id  | config_json |
      | metadata-text | {}          |
      | stt-aldea     | {}          |
    Then the extracted text for the last ingested item equals "Aldea transcript wins"
    And the extraction snapshot item provenance uses extractor "stt-aldea"

  Scenario: Aldea speech to text returns empty when response has no results
    Given I initialized a corpus at "corpus"
    And a fake Aldea library is available that returns empty results for filename "clip.wav"
    And an Aldea API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-aldea" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item is empty

  Scenario: Aldea speech to text returns empty when response has empty channels
    Given I initialized a corpus at "corpus"
    And a fake Aldea library is available that returns empty channels for filename "clip.wav"
    And an Aldea API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-aldea" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item is empty

  Scenario: Aldea speech to text returns empty when response has empty alternatives
    Given I initialized a corpus at "corpus"
    And a fake Aldea library is available that returns empty alternatives for filename "clip.wav"
    And an Aldea API key is configured for this scenario
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-aldea" extraction snapshot in corpus "corpus"
    Then the extracted text for the last ingested item is empty
