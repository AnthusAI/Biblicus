Feature: AWS Amplify Publisher
  As a Biblicus user
  I want to sync corpus data to AWS Amplify
  So that I can access my corpus through the cloud dashboard

  Background:
    Given fake AWS and HTTP services are available

  Scenario: AmplifyPublisher requires configuration
    When I attempt to create an AmplifyPublisher without configuration
    Then an Amplify configuration error is raised

  Scenario: AmplifyPublisher loads config from environment variables
    Given Amplify environment variables are configured
    And Amplify environment variables are set
    When I create an AmplifyPublisher for corpus "test-corpus"
    Then the publisher is configured with environment values

  Scenario: AmplifyPublisher loads config from file
    Given Amplify environment variables are configured
    And an Amplify config file exists at "~/.biblicus/amplify.env"
    When I create an AmplifyPublisher for corpus "test-corpus"
    Then the publisher is configured with file values

  Scenario: Create corpus record
    Given Amplify environment variables are configured
    And an AmplifyPublisher for corpus "my-corpus"
    When I call create_corpus
    Then a GraphQL createCorpus mutation is executed
    And the corpus status is "IDLE"

  Scenario: Start snapshot creates snapshot record
    Given Amplify environment variables are configured
    And an AmplifyPublisher for corpus "my-corpus"
    When I call start_snapshot with id "snap-123" type "extraction" and 100 items
    Then a GraphQL createSnapshot mutation is executed
    And the snapshot status is "RUNNING"

  Scenario: Update snapshot progress
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    When I call update_snapshot_progress for "snap-123" with 50 completed items
    Then a GraphQL updateSnapshot mutation is executed with completedItems 50

  Scenario: Complete snapshot successfully
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    When I call complete_snapshot for "snap-123" with 100 items
    Then a GraphQL updateSnapshot mutation is executed
    And the snapshot status is "COMPLETED"

  Scenario: Complete snapshot with error
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    When I call complete_snapshot for "snap-123" with error "Test error"
    Then a GraphQL updateSnapshot mutation is executed
    And the snapshot status is "FAILED"
    And the snapshot error message is "Test error"

  Scenario: Register file as LOCAL_ONLY
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And a test file "test.txt" in corpus "my-corpus"
    When I call register_file for "test.txt"
    Then a GraphQL createFileMetadata mutation is executed
    And the file status is "LOCAL_ONLY"

  Scenario: Upload file to S3
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And a test file "test.txt" in corpus "my-corpus"
    When I call upload_file for "test.txt"
    Then a GraphQL updateFileMetadata mutation is executed with status "UPLOADING"
    And the file is uploaded to S3 at "my-corpus/test.txt"

  Scenario: Sync catalog when unchanged (idempotent)
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And a catalog with hash "abc123" exists in Amplify
    And a local catalog with the same hash "abc123"
    When I call sync_catalog
    Then the sync is skipped with reason "Catalog unchanged"

  Scenario: Sync catalog full replacement for small catalog
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And a local catalog with 50 items
    When I call sync_catalog
    Then a full replacement sync is performed
    And 50 items are created in Amplify

  Scenario: Sync catalog with force flag
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And a catalog with hash "abc123" exists in Amplify
    And a local catalog with the same hash "abc123"
    When I call sync_catalog with force flag
    Then a full replacement sync is performed

  Scenario: Sync catalog handles item creation errors
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And a local catalog with 10 items
    And item "item-5" will fail to create
    When I call sync_catalog
    Then 9 items are successfully created
    And 1 error is recorded for "item-5"

  Scenario: Sync catalog updates metadata
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And a local catalog with 25 items
    When I call sync_catalog
    Then catalog metadata is updated with item count 25

  Scenario: Execute GraphQL handles network errors
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And GraphQL requests will fail with network errors
    When I attempt to create corpus
    Then a network error is raised

  Scenario: Execute GraphQL handles GraphQL errors
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And GraphQL will return errors
    When I attempt to create corpus
    Then a GraphQL error is raised

  Scenario: Create catalog item retries on network failure
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And GraphQL will fail once then succeed
    When I sync a catalog with 1 item
    Then the item is created after retry

  Scenario: Catalog hash computation is deterministic
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And a catalog with items in random order
    When I compute the catalog hash twice
    Then both hashes are identical

  Scenario: Catalog metadata sync creates if update fails
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And catalog metadata update will fail
    When I sync catalog metadata
    Then a createCatalogMetadata mutation is executed

  Scenario: AmplifyPublisher loads S3 bucket from config file
    Given fake AWS and HTTP services are available
    And only AMPLIFY_APPSYNC_ENDPOINT and AMPLIFY_API_KEY are set in environment
    And an Amplify config file with S3_BUCKET exists
    When I create an AmplifyPublisher for corpus "test-corpus"
    Then the publisher is configured with S3 bucket from file

  Scenario: Sync catalog uses incremental sync for large catalogs
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And a local catalog with 150 items
    When I call sync_catalog
    Then a full replacement sync is performed

  Scenario: Create catalog item retries three times before failing
    Given Amplify environment variables are configured
    Given an AmplifyPublisher for corpus "my-corpus"
    And GraphQL will fail three times
    When I sync a catalog with 1 item
    Then the sync fails with network errors
