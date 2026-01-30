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

  Scenario: HuggingFace API key can be read from configuration
    Given a file ".biblicus/config.yml" exists with contents:
      """
      huggingface:
        api_key: hf-test-key
      """
    When I load user configuration from ".biblicus/config.yml"
    Then the loaded user configuration has HuggingFace API key "hf-test-key"

  Scenario: Resolve HuggingFace API key from environment via helper function
    Given I initialized a corpus at "corpus"
    And the environment variable "HUGGINGFACE_API_KEY" is set to "env-hf-key"
    When I call resolve_huggingface_api_key helper function
    Then the resolved API key equals "env-hf-key"

  Scenario: Resolve HuggingFace API key from config file via helper function
    Given I initialized a corpus at "corpus"
    And a local Biblicus user config exists with HuggingFace API key "config-hf-key"
    When I call resolve_huggingface_api_key helper function
    Then the resolved API key equals "config-hf-key"

  Scenario: Resolve HuggingFace API key returns None when not configured
    Given I initialized a corpus at "corpus"
    When I call resolve_huggingface_api_key helper function
    Then the resolved API key is None

  Scenario: Deepgram API key can be read from configuration
    Given a file ".biblicus/config.yml" exists with contents:
      """
      deepgram:
        api_key: dg-test-key
      """
    When I load user configuration from ".biblicus/config.yml"
    Then the loaded user configuration has Deepgram API key "dg-test-key"

  Scenario: Resolve Deepgram API key from config file via helper function
    Given I initialized a corpus at "corpus"
    And a local Biblicus user config exists with Deepgram API key "config-dg-key"
    When I call resolve_deepgram_api_key helper function
    Then the resolved API key equals "config-dg-key"

  Scenario: Resolve Deepgram API key returns None when not configured
    Given I initialized a corpus at "corpus"
    When I call resolve_deepgram_api_key helper function
    Then the resolved API key is None
