Feature: AWS Transcribe speech to text extraction
  Audio items can produce derived text artifacts through AWS Transcribe STT extractor.
  The raw audio bytes remain unchanged in the corpus root.

  Scenario: AWS Transcribe extractor requires an optional dependency
    Given I initialized a corpus at "corpus"
    And the boto3 dependency is unavailable
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json                                    |
      | stt-aws-transcribe | {"s3_bucket":"test-bucket"}                    |
    Then the command fails with exit code 2
    And standard error includes "biblicus[aws]"

  Scenario: AWS Transcribe extractor skips non-audio items
    Given I initialized a corpus at "corpus"
    And a fake boto3 library is available
    When I ingest the text "alpha" with no metadata into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json                                    |
      | stt-aws-transcribe | {"s3_bucket":"test-bucket"}                    |
    Then the extraction snapshot does not include extracted text for the last ingested item

  Scenario: AWS Transcribe extractor produces transcript for an audio item
    Given I initialized a corpus at "corpus"
    And a fake boto3 library is available that returns transcript "Hello from AWS Transcribe" for filename "clip.wav"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json                                    |
      | stt-aws-transcribe | {"s3_bucket":"test-bucket"}                    |
    Then the extracted text for the last ingested item equals "Hello from AWS Transcribe"
    And the extraction snapshot item provenance uses extractor "stt-aws-transcribe"

  Scenario: AWS Transcribe uses configured language code
    Given I initialized a corpus at "corpus"
    And a fake boto3 library is available that returns transcript "Bonjour" for filename "clip.wav"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json                                            |
      | stt-aws-transcribe | {"s3_bucket":"test-bucket","language_code":"fr-FR"}    |
    Then the extracted text for the last ingested item equals "Bonjour"
    And the AWS Transcribe job used language code "fr-FR"

  Scenario: AWS Transcribe detects media format from media type
    Given I initialized a corpus at "corpus"
    And a fake boto3 library is available that returns transcript "Test audio" for filename "clip.flac"
    And a file "clip.flac" exists with bytes:
      """
      fLaC\x00\x00\x00\x22
      """
    When I ingest the file "clip.flac" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json                                    |
      | stt-aws-transcribe | {"s3_bucket":"test-bucket"}                    |
    Then the extracted text for the last ingested item equals "Test audio"
    And the AWS Transcribe job used media format "flac"

  Scenario: AWS Transcribe handles job failure
    Given I initialized a corpus at "corpus"
    And a fake boto3 library is available that returns failed job for filename "clip.wav" with reason "Invalid audio format"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json                                    |
      | stt-aws-transcribe | {"s3_bucket":"test-bucket"}                    |
    Then the command fails with exit code 2
    And standard error includes "Invalid audio format"

  Scenario: AWS Transcribe enables speaker identification when configured
    Given I initialized a corpus at "corpus"
    And a fake boto3 library is available that returns transcript "Speaker one. Speaker two." for filename "clip.wav"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json                                                                   |
      | stt-aws-transcribe | {"s3_bucket":"test-bucket","identify_speakers":true,"max_speakers":2}        |
    Then the extracted text for the last ingested item equals "Speaker one. Speaker two."
    And the AWS Transcribe job enabled speaker labels

  Scenario: AWS Transcribe handles timeout when job takes too long
    Given I initialized a corpus at "corpus"
    And a fake boto3 library is available that returns in-progress job for filename "clip.wav"
    And a file "clip.wav" exists with bytes:
      """
      RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data
      """
    When I ingest the file "clip.wav" into corpus "corpus"
    And I attempt to build a "pipeline" extraction snapshot in corpus "corpus" with stages:
      | extractor_id       | config_json                                          |
      | stt-aws-transcribe | {"s3_bucket":"test-bucket","max_wait_seconds":1}     |
    Then the command fails with exit code 2
    And standard error includes "timed out"
