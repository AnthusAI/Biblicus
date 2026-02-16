Feature: Azure STT extractor handles missing API key
  The Azure speech-to-text extractor should fail fast when the API key is absent even if the SDK is installed.

  Scenario: Azure STT raises when AZURE_SPEECH_KEY is missing
    Given fake azure speech sdk is available
    And environment variable "AZURE_SPEECH_KEY" is unset
    When I run the azure speech extractor directly with item "clip.wav"
    Then the extraction fails with a fatal error containing "Azure Speech speech to text extractor requires an Azure Speech API key"
