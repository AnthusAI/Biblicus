"""Step definitions for AWS Amplify Publisher BDD tests."""
from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

from behave import given, then, when


def _install_fake_boto3_and_requests(context):
    """Install fake boto3 and requests modules."""
    # Always set up context attributes, even if modules already installed
    already_installed = "boto3" in sys.modules and "requests" in sys.modules and hasattr(sys.modules["boto3"], "_is_fake")

    # Store originals
    if not hasattr(context, '_original_modules'):
        context._original_modules = {}
        for name in ["boto3", "requests"]:
            if name in sys.modules and not already_installed:
                context._original_modules[name] = sys.modules[name]

    # Create fake S3 client
    class FakeS3Client:
        def __init__(self):
            self.uploaded_files: Dict[str, bytes] = {}

        def put_object(self, Bucket: str, Key: str, Body):
            content = Body.read() if hasattr(Body, 'read') else Body
            self.uploaded_files[f"{Bucket}/{Key}"] = content

    context.fake_s3_client = FakeS3Client()

    if already_installed:
        # Modules already installed, just set up context attributes
        context.graphql_requests = []
        context.graphql_responses = []
        context.graphql_errors = []
        context._fake_aws_installed = True
        return

    # Create fake boto3
    boto3_module = types.ModuleType("boto3")
    boto3_module._is_fake = True  # Mark as fake for detection

    def client(service_name: str, region_name: str = None):
        if service_name == 's3':
            return context.fake_s3_client
        raise ValueError(f"Unknown service: {service_name}")

    boto3_module.client = client

    # Create fake requests
    requests_module = types.ModuleType("requests")
    context.graphql_requests: List[Dict[str, Any]] = []
    context.graphql_responses: List[Dict[str, Any]] = []
    context.graphql_errors: List[Exception] = []

    class FakeResponse:
        def __init__(self, json_data: Dict, status_code: int = 200):
            self._json_data = json_data
            self.status_code = status_code

        def json(self):
            return self._json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

    def post(url: str, headers: Dict = None, json: Dict = None, timeout: int = None):
        context.graphql_requests.append({
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout
        })

        # Check for configured errors
        if context.graphql_errors:
            error = context.graphql_errors.pop(0)
            raise error

        # Check for configured responses
        if context.graphql_responses:
            response_data = context.graphql_responses.pop(0)
            return FakeResponse(response_data)

        # Default: successful response
        query = json.get('query', '')
        if 'createCorpus' in query:
            return FakeResponse({"data": {"createCorpus": {"name": "test", "s3Prefix": "test", "status": "IDLE"}}})
        elif 'createSnapshot' in query:
            return FakeResponse({"data": {"createSnapshot": {"corpusId": "test", "snapshotId": "snap-1", "status": "RUNNING", "totalItems": 100}}})
        elif 'updateSnapshot' in query:
            response_data = {"corpusId": "test", "snapshotId": "snap-1", "completedItems": 50}
            # Include status if provided in the mutation variables
            if json and "variables" in json and "input" in json["variables"]:
                input_vars = json["variables"]["input"]
                if "status" in input_vars:
                    response_data["status"] = input_vars["status"]
                if "errorMessage" in input_vars:
                    response_data["errorMessage"] = input_vars["errorMessage"]
            return FakeResponse({"data": {"updateSnapshot": response_data}})
        elif 'createFileMetadata' in query:
            return FakeResponse({"data": {"createFileMetadata": {"corpusId": "test", "filePath": "test.txt", "status": "LOCAL_ONLY"}}})
        elif 'updateFileMetadata' in query:
            return FakeResponse({"data": {"updateFileMetadata": {"corpusId": "test", "filePath": "test.txt", "status": "UPLOADING"}}})
        elif 'createCatalogItem' in query:
            return FakeResponse({"data": {"createCatalogItem": {"corpusId": "test", "itemId": "item-1"}}})
        elif 'updateCatalogMetadata' in query:
            return FakeResponse({"data": {"updateCatalogMetadata": {"corpusId": "test", "catalogHash": "abc123"}}})
        elif 'createCatalogMetadata' in query:
            return FakeResponse({"data": {"createCatalogMetadata": {"corpusId": "test", "catalogHash": "abc123"}}})
        elif 'getCatalogMetadata' in query:
            return FakeResponse({"data": {"getCatalogMetadata": None}})
        else:
            return FakeResponse({"data": {}})

    requests_module.post = post

    sys.modules["boto3"] = boto3_module
    sys.modules["requests"] = requests_module
    context._fake_aws_installed = True


@given("fake AWS and HTTP services are available")
def step_fake_aws_available(context):
    _install_fake_boto3_and_requests(context)


def _ensure_fake_aws_installed(context):
    """Ensure fake AWS is installed before using context attributes."""
    if not getattr(context, "_fake_aws_installed", False):
        _install_fake_boto3_and_requests(context)


@given("Amplify environment variables are configured")
def step_amplify_env_configured(context):
    _ensure_fake_aws_installed(context)
    context.amplify_env = {
        "AMPLIFY_APPSYNC_ENDPOINT": "https://fake.appsync-api.us-west-2.amazonaws.com/graphql",
        "AMPLIFY_API_KEY": "fake-api-key-123",
        "AWS_REGION": "us-west-2",
        "AMPLIFY_S3_BUCKET": "fake-bucket"
    }
    for key, value in context.amplify_env.items():
        os.environ[key] = value


@given("Amplify environment variables are set")
def step_amplify_env_set(context):
    step_amplify_env_configured(context)


@given('an Amplify config file exists at "{path}"')
def step_amplify_config_file_exists(context, path: str):
    # Clear environment variables to test file-based config
    for key in ["AMPLIFY_APPSYNC_ENDPOINT", "AMPLIFY_API_KEY", "AWS_REGION", "AMPLIFY_S3_BUCKET"]:
        os.environ.pop(key, None)

    # Expand ~ to actual home directory
    config_path = Path.home() / '.biblicus' / 'amplify.env'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("""# Amplify Configuration
AMPLIFY_APPSYNC_ENDPOINT=https://file.appsync-api.us-west-2.amazonaws.com/graphql
AMPLIFY_API_KEY=file-api-key-456
AWS_REGION=us-east-1
AMPLIFY_S3_BUCKET=file-bucket
""")
    context.amplify_config_path = config_path


@when("I attempt to create an AmplifyPublisher without configuration")
def step_create_publisher_without_config(context):
    _ensure_fake_aws_installed(context)

    # Clear all env vars
    for key in ["AMPLIFY_APPSYNC_ENDPOINT", "AMPLIFY_API_KEY", "AMPLIFY_S3_BUCKET", "AWS_REGION"]:
        os.environ.pop(key, None)

    # Also remove the config file if it exists
    config_path = Path.home() / '.biblicus' / 'amplify.env'
    if config_path.exists():
        config_path.unlink()

    try:
        from biblicus.sync.amplify_publisher import AmplifyPublisher
        AmplifyPublisher("test-corpus")
        context.amplify_error = None
    except Exception as e:
        context.amplify_error = e


@then("an Amplify configuration error is raised")
def step_amplify_config_error_raised(context):
    error = getattr(context, 'amplify_error', None)
    assert error is not None, f"Expected error but got None. Context attributes: {dir(context)}"
    assert "Missing required Amplify configuration" in str(error), f"Expected config error, got: {error}"


@when('I create an AmplifyPublisher for corpus "{corpus_name}"')
def step_create_publisher(context, corpus_name: str):
    _ensure_fake_aws_installed(context)
    from biblicus.sync.amplify_publisher import AmplifyPublisher
    context.publisher = AmplifyPublisher(corpus_name)


@given('an AmplifyPublisher for corpus "{corpus_name}"')
def step_given_publisher(context, corpus_name: str):
    step_create_publisher(context, corpus_name)


@then("the publisher is configured with environment values")
def step_publisher_configured_from_env(context):
    assert context.publisher.appsync_endpoint == context.amplify_env["AMPLIFY_APPSYNC_ENDPOINT"]
    assert context.publisher.api_key == context.amplify_env["AMPLIFY_API_KEY"]
    assert context.publisher.s3_bucket == context.amplify_env["AMPLIFY_S3_BUCKET"]


@then("the publisher is configured with file values")
def step_publisher_configured_from_file(context):
    assert context.publisher.appsync_endpoint == "https://file.appsync-api.us-west-2.amazonaws.com/graphql"
    assert context.publisher.api_key == "file-api-key-456"
    assert context.publisher.region == "us-east-1"
    assert context.publisher.s3_bucket == "file-bucket"


@when("I call create_corpus")
def step_call_create_corpus(context):
    context.create_corpus_result = context.publisher.create_corpus()


@then("a GraphQL createCorpus mutation is executed")
def step_create_corpus_mutation_executed(context):
    assert len(context.graphql_requests) > 0
    request = context.graphql_requests[-1]
    assert "createCorpus" in request["json"]["query"]


@then('the corpus status is "{status}"')
def step_corpus_status_is(context, status: str):
    assert context.create_corpus_result["createCorpus"]["status"] == status


@when('I call start_snapshot with id "{snapshot_id}" type "{snapshot_type}" and {total_items:d} items')
def step_call_start_snapshot(context, snapshot_id: str, snapshot_type: str, total_items: int):
    context.snapshot_result = context.publisher.start_snapshot(snapshot_id, snapshot_type, total_items)


@then("a GraphQL createSnapshot mutation is executed")
def step_create_snapshot_mutation_executed(context):
    request = context.graphql_requests[-1]
    assert "createSnapshot" in request["json"]["query"]


@then('the snapshot status is "{status}"')
def step_snapshot_status_is(context, status: str):
    # Check in the appropriate result based on which operation was last called
    if hasattr(context, "snapshot_result"):
        assert context.snapshot_result["createSnapshot"]["status"] == status
    elif hasattr(context, "complete_result"):
        assert context.complete_result["updateSnapshot"]["status"] == status
    else:
        raise AssertionError("No snapshot result found in context")


@when('I call update_snapshot_progress for "{snapshot_id}" with {completed_items:d} completed items')
def step_call_update_snapshot_progress(context, snapshot_id: str, completed_items: int):
    context.update_result = context.publisher.update_snapshot_progress(snapshot_id, completed_items)


@then("a GraphQL updateSnapshot mutation is executed with completedItems {count:d}")
def step_update_snapshot_mutation_executed(context, count: int):
    request = context.graphql_requests[-1]
    assert "updateSnapshot" in request["json"]["query"]
    assert request["json"]["variables"]["input"]["completedItems"] == count


@when('I call complete_snapshot for "{snapshot_id}" with {total_items:d} items')
def step_call_complete_snapshot(context, snapshot_id: str, total_items: int):
    context.complete_result = context.publisher.complete_snapshot(snapshot_id, total_items)


@when('I call complete_snapshot for "{snapshot_id}" with error "{error_message}"')
def step_call_complete_snapshot_with_error(context, snapshot_id: str, error_message: str):
    context.complete_result = context.publisher.complete_snapshot(snapshot_id, 0, error_message)


@then("a GraphQL updateSnapshot mutation is executed")
def step_update_snapshot_mutation(context):
    request = context.graphql_requests[-1]
    assert "updateSnapshot" in request["json"]["query"]


@then('the snapshot error message is "{error_message}"')
def step_snapshot_error_message(context, error_message: str):
    request = context.graphql_requests[-1]
    assert request["json"]["variables"]["input"]["errorMessage"] == error_message


@given('a test file "{filename}" in corpus "{corpus_name}"')
def step_test_file_in_corpus(context, filename: str, corpus_name: str):
    corpus_dir = context.workdir / corpus_name
    corpus_dir.mkdir(parents=True, exist_ok=True)
    file_path = corpus_dir / filename
    file_path.write_text("test content")
    context.test_file_path = file_path
    context.corpus_dir = corpus_dir


@when('I call register_file for "{filename}"')
def step_call_register_file(context, filename: str):
    context.register_result = context.publisher.register_file(
        str(context.test_file_path),
        context.corpus_dir
    )


@then("a GraphQL createFileMetadata mutation is executed")
def step_create_file_metadata_mutation(context):
    request = context.graphql_requests[-1]
    assert "createFileMetadata" in request["json"]["query"]


@then('the file status is "{status}"')
def step_file_status_is(context, status: str):
    assert context.register_result["createFileMetadata"]["status"] == status


@when('I call upload_file for "{filename}"')
def step_call_upload_file(context, filename: str):
    context.upload_result = context.publisher.upload_file(
        context.test_file_path,
        context.corpus_dir
    )


@then('a GraphQL updateFileMetadata mutation is executed with status "{status}"')
def step_update_file_metadata_mutation(context, status: str):
    # Find the updateFileMetadata request
    update_requests = [r for r in context.graphql_requests if "updateFileMetadata" in r["json"]["query"]]
    assert len(update_requests) > 0
    assert update_requests[0]["json"]["variables"]["input"]["status"] == status


@then('the file is uploaded to S3 at "{s3_key}"')
def step_file_uploaded_to_s3(context, s3_key: str):
    full_key = f"fake-bucket/{s3_key}"
    assert full_key in context.fake_s3_client.uploaded_files
    assert context.fake_s3_client.uploaded_files[full_key] == b"test content"


@given('a catalog with hash "{catalog_hash}" exists in Amplify')
def step_catalog_with_hash_exists(context, catalog_hash: str):
    # Store the expected hash, will be set correctly when catalog is created
    context.expected_catalog_hash = catalog_hash
    context.remote_catalog_exists = True


@given('a local catalog with the same hash "{catalog_hash}"')
@given('a local catalog with {item_count:d} items')
def step_local_catalog(context, catalog_hash: str = None, item_count: int = None):
    from biblicus.models import CatalogItem, CorpusCatalog

    if item_count is None:
        item_count = 50

    items = {}
    for i in range(item_count):
        item = CatalogItem(
            id=f"item-{i}",
            relpath=f"item-{i}.txt",
            sha256=f"sha256-{i}",
            bytes=100,
            media_type="text/plain",
            tags=[],
            metadata={},
            created_at="2024-01-01T00:00:00Z",
            source_uri="test"
        )
        items[item.id] = item

    catalog = CorpusCatalog(
        schema_version=2,
        generated_at="2024-01-01T00:00:00Z",
        corpus_uri="file://my-corpus",
        items=items,
        order=list(items.keys())
    )

    catalog_path = context.workdir / "catalog.json"
    catalog_path.write_text(catalog.model_dump_json())
    context.catalog_path = catalog_path
    context.catalog = catalog

    # If remote catalog exists with expected hash, compute actual hash and configure response
    if hasattr(context, "remote_catalog_exists") and context.remote_catalog_exists:
        import hashlib
        import json as json_module
        items_data = sorted([
            (item.id, item.sha256, item.relpath)
            for item in catalog.items.values()
        ])
        actual_hash = hashlib.sha256(json_module.dumps(items_data).encode()).hexdigest()

        # Configure the getCatalogMetadata response
        context.graphql_responses.append({
            "data": {
                "getCatalogMetadata": {
                    "corpusId": "my-corpus",
                    "catalogHash": actual_hash,
                    "itemCount": item_count,
                    "lastSyncedAt": "2024-01-01T00:00:00Z"
                }
            }
        })


@when("I call sync_catalog")
def step_call_sync_catalog(context):
    context.sync_result = context.publisher.sync_catalog(context.catalog_path)


@when("I call sync_catalog with force flag")
def step_call_sync_catalog_force(context):
    context.sync_result = context.publisher.sync_catalog(context.catalog_path, force=True)


@then('the sync is skipped with reason "{reason}"')
def step_sync_skipped(context, reason: str):
    assert context.sync_result.skipped is True
    assert reason in context.sync_result.reason


@then("a full replacement sync is performed")
def step_full_replacement_sync(context):
    assert context.sync_result.skipped is False
    assert context.sync_result.created > 0


@then("{count:d} items are created in Amplify")
@then("{count:d} items are successfully created")
def step_items_created(context, count: int):
    assert context.sync_result.created == count


@given('item "{item_id}" will fail to create')
def step_item_will_fail(context, item_id: str):
    # Configure responses based on which item should fail
    # Extract the item number from item_id (e.g., "item-5" -> 5)
    item_num = int(item_id.split("-")[1])

    # First response is for getCatalogMetadata query (returns None to trigger sync)
    responses = [{"data": {"getCatalogMetadata": None}}]

    # Then responses for createCatalogItem mutations for items 0-9
    for i in range(10):
        if i == item_num:
            responses.append({"errors": [{"message": "Simulated failure"}]})
        else:
            responses.append({"data": {"createCatalogItem": {"corpusId": "my-corpus", "itemId": f"item-{i}"}}})

    context.graphql_responses = responses


@then('{count:d} error is recorded for "{item_id}"')
def step_error_recorded(context, count: int, item_id: str):
    assert len(context.sync_result.errors) == count, f"Expected {count} errors, got {len(context.sync_result.errors)}: {context.sync_result.errors}"
    assert any(item_id in error for error in context.sync_result.errors), f"Expected to find '{item_id}' in errors: {context.sync_result.errors}"


@then("catalog metadata is updated with item count {count:d}")
def step_catalog_metadata_updated(context, count: int):
    # Find updateCatalogMetadata or createCatalogMetadata request
    metadata_requests = [r for r in context.graphql_requests
                        if "CatalogMetadata" in r["json"]["query"]]
    assert len(metadata_requests) > 0
    assert metadata_requests[-1]["json"]["variables"]["input"]["itemCount"] == count


@given("GraphQL requests will fail with network errors")
def step_graphql_will_fail_network(context):
    context.graphql_errors = [Exception("Network error")]


@when("I attempt to create corpus")
def step_attempt_create_corpus(context):
    try:
        context.publisher.create_corpus()
        context.graphql_error = None
    except Exception as e:
        context.graphql_error = e


@then("a network error is raised")
def step_network_error_raised(context):
    assert context.graphql_error is not None
    assert "Network error" in str(context.graphql_error)


@given("GraphQL will return errors")
def step_graphql_will_return_errors(context):
    context.graphql_responses = [{"errors": [{"message": "GraphQL error"}]}]


@then("a GraphQL error is raised")
def step_graphql_error_raised(context):
    assert context.graphql_error is not None
    assert "GraphQL errors" in str(context.graphql_error)


@given("GraphQL will fail once then succeed")
def step_graphql_fail_then_succeed(context):
    context.graphql_errors = [Exception("Network error")]
    context.graphql_responses = [{"data": {"createCatalogItem": {"corpusId": "my-corpus", "itemId": "item-0"}}}]


@when("I sync a catalog with {count:d} item")
def step_sync_catalog_with_items(context, count: int):
    step_local_catalog(context, item_count=count)
    step_call_sync_catalog(context)


@then("the item is created after retry")
def step_item_created_after_retry(context):
    assert context.sync_result.created == 1
    assert len(context.sync_result.errors) == 0


@given("a catalog with items in random order")
def step_catalog_random_order(context):
    step_local_catalog(context, item_count=10)


@when("I compute the catalog hash twice")
def step_compute_hash_twice(context):
    hash1 = context.publisher._compute_catalog_hash(context.catalog)
    hash2 = context.publisher._compute_catalog_hash(context.catalog)
    context.hash1 = hash1
    context.hash2 = hash2


@then("both hashes are identical")
def step_hashes_identical(context):
    assert context.hash1 == context.hash2


@given("catalog metadata update will fail")
def step_catalog_metadata_update_fails(context):
    context.graphql_responses = [
        {"errors": [{"message": "Update failed"}]},  # First attempt fails
        {"data": {"createCatalogMetadata": {"corpusId": "my-corpus", "catalogHash": "abc123"}}}  # Create succeeds
    ]


@when("I sync catalog metadata")
def step_sync_catalog_metadata(context):
    step_local_catalog(context, item_count=5)
    catalog_hash = context.publisher._compute_catalog_hash(context.catalog)
    context.publisher._sync_catalog_metadata(context.catalog, catalog_hash)


@then("a createCatalogMetadata mutation is executed")
def step_create_catalog_metadata_mutation(context):
    create_requests = [r for r in context.graphql_requests
                      if "createCatalogMetadata" in r["json"]["query"]]
    assert len(create_requests) > 0


@given("only AMPLIFY_APPSYNC_ENDPOINT and AMPLIFY_API_KEY are set in environment")
def step_partial_env_vars(context):
    step_amplify_env_configured(context)
    # Only set endpoint and API key, not S3 bucket
    os.environ["AMPLIFY_APPSYNC_ENDPOINT"] = context.amplify_env["AMPLIFY_APPSYNC_ENDPOINT"]
    os.environ["AMPLIFY_API_KEY"] = context.amplify_env["AMPLIFY_API_KEY"]
    os.environ.pop("AMPLIFY_S3_BUCKET", None)


@given("an Amplify config file with S3_BUCKET exists")
def step_config_file_with_bucket(context):
    config_path = Path.home() / '.biblicus' / 'amplify.env'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("AMPLIFY_S3_BUCKET=file-bucket-from-config\n")
    context.amplify_config_path = config_path


@then("the publisher is configured with S3 bucket from file")
def step_publisher_has_file_bucket(context):
    assert context.publisher.s3_bucket == "file-bucket-from-config"


@given("GraphQL will fail three times")
def step_graphql_fail_three_times(context):
    # Don't set graphql_responses - let getCatalogMetadata fail and return None
    # Add four network errors:
    # 1. getCatalogMetadata will fail (caught and returns None)
    # 2-4. createCatalogItem will fail on all 3 retry attempts
    context.graphql_errors.append(Exception("Network error"))
    context.graphql_errors.append(Exception("Network error"))
    context.graphql_errors.append(Exception("Network error"))
    context.graphql_errors.append(Exception("Network error"))


@then("the sync fails with network errors")
def step_sync_fails(context):
    assert len(context.sync_result.errors) > 0, f"Expected errors but got: {context.sync_result}"
    error_msg = context.sync_result.errors[0]
    assert "Network error" in error_msg or "Failed to sync" in error_msg, f"Expected network error but got: {error_msg}"
