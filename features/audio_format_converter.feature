Feature: Audio format conversion
  Audio items can be converted between formats for compatibility with downstream extractors.
  The converter creates new corpus items in the target format.

  Scenario: Audio converter requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the pydub dependency is unavailable
    And a file "clip.flac" exists with bytes:
      """
      fLaC\x00\x00\x00\x22
      """
    When I ingest the file "clip.flac" into corpus "corpus"
    And I attempt to build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id             | config_json                    |
      | audio-format-converter   | {"target_format":"wav"}       |
    Then the command fails with exit code 2
    And standard error includes "biblicus[audio]"

  Scenario: Audio converter skips non-audio items
    Given I initialized a corpus at "corpus"
    And a fake pydub library is available
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id             | config_json                    |
      | audio-format-converter   | {"target_format":"wav"}       |
    Then the extraction snapshot does not include extracted text for the last ingested item

  Scenario: Audio converter converts FLAC to WAV
    Given I initialized a corpus at "corpus"
    And a fake pydub library is available
    And a file "clip.flac" exists with bytes:
      """
      fLaC\x00\x00\x00\x22
      """
    When I ingest the file "clip.flac" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id             | config_json                    |
      | audio-format-converter   | {"target_format":"wav"}       |
    Then the extraction snapshot item provenance uses extractor "audio-format-converter"
    And the audio conversion loaded format "flac"
    And the audio conversion exported format "wav"

  Scenario: Audio converter skips conversion when already in target format
    Given I initialized a corpus at "corpus"
    And a fake pydub library is available
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id             | config_json                    |
      | audio-format-converter   | {"target_format":"wav"}       |
    Then the extraction snapshot item provenance uses extractor "audio-format-converter"

  Scenario: Audio converter applies sample rate conversion
    Given I initialized a corpus at "corpus"
    And a fake pydub library is available
    And a file "clip.flac" exists with bytes:
      """
      fLaC\x00\x00\x00\x22
      """
    When I ingest the file "clip.flac" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id             | config_json                                              |
      | audio-format-converter   | {"target_format":"wav","sample_rate":16000}             |
    Then the extraction snapshot item provenance uses extractor "audio-format-converter"
    And the audio conversion set frame rate to 16000

  Scenario: Audio converter applies channel conversion
    Given I initialized a corpus at "corpus"
    And a fake pydub library is available
    And a file "clip.flac" exists with bytes:
      """
      fLaC\x00\x00\x00\x22
      """
    When I ingest the file "clip.flac" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id             | config_json                                       |
      | audio-format-converter   | {"target_format":"wav","channels":1}             |
    Then the extraction snapshot item provenance uses extractor "audio-format-converter"
    And the audio conversion set channels to 1

  Scenario: Audio converter converts OGG to MP3
    Given I initialized a corpus at "corpus"
    And a fake pydub library is available
    And a file "clip.ogg" exists with bytes:
      """
      OggS
      """
    When I ingest the file "clip.ogg" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id             | config_json                    |
      | audio-format-converter   | {"target_format":"mp3"}       |
    Then the extraction snapshot item provenance uses extractor "audio-format-converter"
    And the audio conversion loaded format "ogg"
    And the audio conversion exported format "mp3"

  Scenario: Audio converter rejects invalid target format
    Given I initialized a corpus at "corpus"
    And a fake pydub library is available
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id             | config_json                       |
      | audio-format-converter   | {"target_format":"invalid"}      |
    Then the command fails with exit code 2
    And standard error includes "Invalid target_format"
