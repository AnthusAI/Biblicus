Feature: User configuration files
  Biblicus can load user configuration files from home and local locations.
  These files are used for optional integrations such as speech to text.

  Scenario: OpenAI speech to text can read the API key from the local configuration file
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns transcript "ok" for filename "clip.wav"
    And a local Biblicus user config exists with OpenAI API key "local-key"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-openai" extraction run in corpus "corpus"
    Then the extracted text for the last ingested item equals "ok"
    And the OpenAI client was configured with API key "local-key"

  Scenario: Local configuration overrides home configuration
    Given I initialized a corpus at "corpus"
    And a fake OpenAI library is available that returns transcript "ok" for filename "clip.wav"
    And a home Biblicus user config exists with OpenAI API key "home-key"
    And a local Biblicus user config exists with OpenAI API key "local-key"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "stt-openai" extraction run in corpus "corpus"
    Then the OpenAI client was configured with API key "local-key"

  Scenario: Non-mapping YAML configuration is treated as empty configuration
    Given a file ".biblicus/config.yml" exists with contents:
      """
      - not
      - a
      - mapping
      """
    When I load user configuration from ".biblicus/config.yml"
    Then no OpenAI API key is present in the loaded user configuration
