# Biblicus Corpus Viewer - Implementation Plan

## Overview

A serverless real-time corpus viewer built with AWS Amplify Gen 2 and Vite + React. Provides dashboard and drill-down views of Biblicus corpus data with smooth GSAP animations, real-time updates, and deep-linkable URLs for stakeholder sharing.

## Architecture

### Core Technologies
- **AWS Amplify Gen 2**: Complete serverless backend (GraphQL, DynamoDB, S3, Cognito, Hosting)
- **Vite + React**: Fast dev experience with React Router for client-side routing
- **GSAP**: Animation library for smooth transitions
- **TypeScript**: Type-safe development

### Data Flow

```
Python CLI → AppSync (Intent Events) → Frontend (Instant Update)
     ↓
   S3 Upload
     ↓
S3 Events → Lambda → AppSync (Availability Events) → Frontend (Content Ready)
```

## Current Status (2026-02-07)

### Implemented
- **Amplify Backend**: Schema, Auth, Storage, and S3 Event Handler implemented.
- **Python CLI**: Integration mostly complete (needs final testing).
- **Frontend Dashboard**:
    - Project initialized with Vite + React + TypeScript + Tailwind.
    - **GSAP Flip Navigation System**:
        - `StackManager`: Orchestrates navigation stack and manages the "drill-down" animation flow using GSAP Flip.
        - `Breadcrumb`: Components morph from full cards in the grid to collapsed breadcrumbs.
        - `RootView`, `CorpusView`, `ItemView`: Views implemented with GSAP Flip targeting hooks.
        - **Appearance Sidebar**: Floating sidebar with animated theme/mode/motion toggles.
        - **Centralized Data Cache**: `StackManager` now holds `corpus` and `item` data to ensure synchronous rendering during navigation transitions (fixes "pop" effect).
    - **Design System**:
        - Strict flat design (no borders, fuzzy shadows).
        - Radix-based color themes (Cool, Warm, Neutral) with Light/Dark/System modes.
        - Consistent 1em icon sizing and baseline alignment.

### Critical Issues & Blockers
- **Animation Glitch (Corpus Disappearance)**:
    - **Symptom**: When navigating BACK from a Corpus view to the Root grid (clicking "Biblicus"), the Corpus element disappears immediately at the start of the animation, then expands into place at the end. It does not morph smoothly.
    - **Cause**: GSAP Flip fails to link the "leaving" breadcrumb element to the "entering" grid card element. This breaks the morph transition, causing it to fall back to separate fade-out/fade-in animations.
    - **Suspected Root Cause**:
        - **Identity/Targeting**: Despite strict ID matching (`data-flip-id`), Flip sees them as different elements. This is often due to DOM timing (one element removed before the other exists) or duplicate IDs during the transition frame.
        - **Data deduplication**: Strict deduplication was added to `StackManager` to prevent duplicate keys, but the issue persists.
        - **Scoped Selection**: Attempted to scope `Flip.getState` to `containerRef` to avoid global selector pollution, but debugging is ongoing.
    - **Next Steps**:
        - Validate that the target element exists *in the DOM* and has the correct `data-flip-id` at the exact moment `Flip.from` is called.
        - Use `Flip.fit()` manually if automatic state tracking continues to fail.
        - Verify `layout` property changes (display: flex vs block) aren't interfering with Flip's calculations.

### Implementation Phases


### Phase 1: Amplify Backend Setup

#### 1.1 Initialize Amplify Project
```bash
cd biblicus-viewer
npm create amplify@latest
npm install
```

#### 1.2 Define Data Schema
**File**: `amplify/data/resource.ts`

```typescript
import { type ClientSchema, a, defineData } from '@aws-amplify/backend';

const schema = a.schema({
  Corpus: a.model({
    name: a.string().required(),
    s3Prefix: a.string().required(),
    lastActivity: a.datetime(),
    status: a.enum(['IDLE', 'ACTIVE', 'SYNCING']),
    createdAt: a.datetime(),
    updatedAt: a.datetime(),
  })
  .authorization((allow) => [
    allow.owner(),
    allow.authenticated().to(['read'])
  ]),

  Snapshot: a.model({
    corpusId: a.id().required(),
    snapshotId: a.string().required(),
    type: a.enum(['EXTRACTION', 'ANALYSIS', 'GRAPH', 'RETRIEVAL']),
    status: a.enum(['PENDING', 'RUNNING', 'COMPLETED', 'FAILED']),
    totalItems: a.integer(),
    completedItems: a.integer(),
    startTime: a.datetime(),
    endTime: a.datetime(),
    errorMessage: a.string(),
  })
  .authorization((allow) => [
    allow.owner(),
    allow.authenticated().to(['read'])
  ])
  .identifier(['corpusId', 'snapshotId']),

  FileMetadata: a.model({
    corpusId: a.id().required(),
    filePath: a.string().required(),
    status: a.enum(['LOCAL_ONLY', 'UPLOADING', 'AVAILABLE']),
    s3Key: a.string(),
    size: a.integer(),
    uploadedAt: a.datetime(),
  })
  .authorization((allow) => [
    allow.owner(),
    allow.authenticated().to(['read'])
  ])
  .identifier(['corpusId', 'filePath']),

  CatalogMetadata: a.model({
    corpusId: a.id().required(),
    catalogHash: a.string().required(),
    itemCount: a.integer().required(),
    lastSyncedAt: a.datetime().required(),
    schemaVersion: a.integer().required(),
    configurationId: a.string(),
    corpusUri: a.string(),
  })
  .authorization((allow) => [
    allow.owner(),
    allow.authenticated().to(['read'])
  ]),

  CatalogItem: a.model({
    corpusId: a.id().required(),
    itemId: a.string().required(),
    relpath: a.string().required(),
    sha256: a.string().required(),
    bytes: a.integer().required(),
    mediaType: a.string().required(),
    title: a.string(),
    tags: a.string().array(),
    metadataJson: a.json(),
    createdAt: a.datetime().required(),
    sourceUri: a.string(),
    hasExtraction: a.boolean().default(false),
  })
  .authorization((allow) => [
    allow.owner(),
    allow.authenticated().to(['read'])
  ])
  .identifier(['corpusId', 'itemId'])
  .secondaryIndexes((index) => [
    index('mediaType').sortKeys(['createdAt']).queryField('itemsByMediaType'),
    index('tags').sortKeys(['createdAt']).queryField('itemsByTag'),
    index('hasExtraction').sortKeys(['createdAt']).queryField('itemsByExtractionStatus'),
  ]),
});

export type Schema = ClientSchema<typeof schema>;
export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'userPool',  // Frontend uses Cognito
    apiKeyAuthorizationMode: { expiresInDays: 365 }  // Python CLI uses API key
  },
});
```

#### 1.3 Configure Storage
**File**: `amplify/storage/resource.ts`

```typescript
import { defineStorage } from '@aws-amplify/backend';

export const storage = defineStorage({
  name: 'biblicusCorpus',
  access: (allow) => ({
    'corpus/{entity_id}/*': [
      allow.entity('identity').to(['read', 'write', 'delete']),
    ],
    'public/*': [
      allow.guest.to(['read']),
      allow.authenticated.to(['read', 'write']),
    ],
  }),
});
```

#### 1.4 Configure Auth
**File**: `amplify/auth/resource.ts`

```typescript
import { defineAuth } from '@aws-amplify/backend';

export const auth = defineAuth({
  loginWith: {
    email: true,
  },
  userAttributes: {
    email: {
      required: true,
      mutable: true,
    },
  },
});
```

#### 1.5 Wire Backend
**File**: `amplify/backend.ts`

```typescript
import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { storage } from './storage/resource';
import { s3EventHandler } from './functions/s3-event-handler/resource';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as iam from 'aws-cdk-lib/aws-iam';

export const backend = defineBackend({
  auth,
  data,
  storage,
  s3EventHandler,
});

// Add S3 event notification for availability phase
// Note: No prefix filter - all objects trigger Lambda
const s3Bucket = backend.storage.resources.bucket;
s3Bucket.addEventNotification(
  s3.EventType.OBJECT_CREATED,
  new s3n.LambdaDestination(backend.s3EventHandler.resources.lambda)
);

// Grant Lambda permissions to call AppSync
backend.s3EventHandler.resources.lambda.addToRolePolicy(
  new iam.PolicyStatement({
    actions: ['appsync:GraphQL'],
    resources: [backend.data.resources.graphqlApi.arn + '/*'],
  })
);

// Inject AppSync endpoint into Lambda environment
backend.s3EventHandler.resources.lambda.addEnvironment(
  'APPSYNC_ENDPOINT',
  backend.data.resources.graphqlApi.graphqlUrl
);
```

#### 1.6 S3 Event Handler Lambda
**File**: `amplify/functions/s3-event-handler/handler.ts`

```typescript
import { S3Event } from 'aws-lambda';
import { SignatureV4 } from '@aws-sdk/signature-v4';
import { Sha256 } from '@aws-crypto/sha256-js';
import { HttpRequest } from '@aws-sdk/protocol-http';

const APPSYNC_ENDPOINT = process.env.APPSYNC_ENDPOINT!;
const AWS_REGION = process.env.AWS_REGION!;

export const handler = async (event: S3Event) => {
  for (const record of event.Records) {
    const s3Key = record.s3.object.key;

    // Parse corpus structure: {corpusName}/...
    const parts = s3Key.split('/');
    if (parts.length < 2) continue;

    const [corpusName, ...pathParts] = parts;
    const corpusId = corpusName;
    const filePath = pathParts.join('/');

    // Update FileMetadata to AVAILABLE
    const mutation = `
      mutation UpdateFileMetadata($input: UpdateFileMetadataInput!) {
        updateFileMetadata(input: $input) {
          corpusId
          filePath
          status
        }
      }
    `;

    const variables = {
      input: {
        corpusId,
        filePath,
        status: 'AVAILABLE',
        s3Key,
        size: record.s3.object.size,
        uploadedAt: new Date().toISOString(),
      }
    };

    await executeGraphQL(mutation, variables);
  }
};

async function executeGraphQL(query: string, variables: any) {
  const endpoint = new URL(APPSYNC_ENDPOINT);
  const signer = new SignatureV4({
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
      sessionToken: process.env.AWS_SESSION_TOKEN,
    },
    region: AWS_REGION,
    service: 'appsync',
    sha256: Sha256,
  });

  const requestToBeSigned = new HttpRequest({
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      host: endpoint.host,
    },
    hostname: endpoint.host,
    path: endpoint.pathname,
    body: JSON.stringify({ query, variables }),
  });

  const signed = await signer.sign(requestToBeSigned);
  const response = await fetch(APPSYNC_ENDPOINT, {
    method: 'POST',
    headers: signed.headers,
    body: signed.body,
  });

  return response.json();
}
```

**File**: `amplify/functions/s3-event-handler/resource.ts`

```typescript
import { defineFunction } from '@aws-amplify/backend';

export const s3EventHandler = defineFunction({
  name: 's3-event-handler',
  entry: './handler.ts',
  runtime: 'nodejs20.x',
  environment: {
    APPSYNC_ENDPOINT: process.env.APPSYNC_ENDPOINT || '',
  },
});
```

### Phase 2: Python CLI Integration

#### 2.1 Amplify Publisher Module
**File**: `src/biblicus/sync/amplify_publisher.py`

```python
import os
import json
import requests
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import boto3
from pathlib import Path

@dataclass
class SyncResult:
    """Result of a catalog sync operation."""
    skipped: bool = False
    reason: str = ""
    created: int = 0
    updated: int = 0
    deleted: int = 0
    errors: List[str] = None
    hash: str = ""

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class AmplifyPublisher:
    """Publishes corpus events to AWS Amplify backend."""

    def __init__(self, corpus_name: str):
        self.corpus_name = corpus_name
        self.appsync_endpoint = os.getenv('AMPLIFY_APPSYNC_ENDPOINT')
        self.api_key = os.getenv('AMPLIFY_API_KEY')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.s3_bucket = os.getenv('AMPLIFY_S3_BUCKET')

        if not all([self.appsync_endpoint, self.api_key, self.s3_bucket]):
            raise ValueError("Missing required Amplify configuration. Run 'biblicus configure amplify'")

        self.s3_client = boto3.client('s3', region_name=self.region)

    def create_corpus(self) -> Dict[str, Any]:
        """Create or update corpus record."""
        mutation = """
        mutation CreateCorpus($input: CreateCorpusInput!) {
          createCorpus(input: $input) {
            name
            s3Prefix
            status
          }
        }
        """
        variables = {
            'input': {
                'name': self.corpus_name,
                's3Prefix': f'{self.corpus_name}',
                'status': 'IDLE',
            }
        }
        return self._execute_graphql(mutation, variables)

    def start_snapshot(
        self,
        snapshot_id: str,
        snapshot_type: str,
        total_items: int
    ) -> Dict[str, Any]:
        """Publish intent event when snapshot starts (before S3)."""
        mutation = """
        mutation CreateSnapshot($input: CreateSnapshotInput!) {
          createSnapshot(input: $input) {
            corpusId
            snapshotId
            status
            totalItems
          }
        }
        """
        variables = {
            'input': {
                'corpusId': self.corpus_name,
                'snapshotId': snapshot_id,
                'type': snapshot_type,
                'status': 'RUNNING',
                'totalItems': total_items,
                'completedItems': 0,
                'startTime': datetime.now(timezone.utc).isoformat(),
            }
        }
        return self._execute_graphql(mutation, variables)

    def update_snapshot_progress(
        self,
        snapshot_id: str,
        completed_items: int
    ) -> Dict[str, Any]:
        """Update snapshot progress during processing."""
        mutation = """
        mutation UpdateSnapshot($input: UpdateSnapshotInput!) {
          updateSnapshot(input: $input) {
            corpusId
            snapshotId
            completedItems
          }
        }
        """
        variables = {
            'input': {
                'corpusId': self.corpus_name,
                'snapshotId': snapshot_id,
                'completedItems': completed_items,
            }
        }
        return self._execute_graphql(mutation, variables)

    def complete_snapshot(
        self,
        snapshot_id: str,
        total_items: int,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark snapshot as completed or failed."""
        mutation = """
        mutation UpdateSnapshot($input: UpdateSnapshotInput!) {
          updateSnapshot(input: $input) {
            corpusId
            snapshotId
            status
          }
        }
        """
        variables = {
            'input': {
                'corpusId': self.corpus_name,
                'snapshotId': snapshot_id,
                'status': 'FAILED' if error_message else 'COMPLETED',
                'completedItems': total_items,
                'endTime': datetime.now(timezone.utc).isoformat(),
            }
        }
        if error_message:
            variables['input']['errorMessage'] = error_message

        return self._execute_graphql(mutation, variables)

    def register_file(
        self,
        file_path: str,
        relative_to: Path
    ) -> Dict[str, Any]:
        """Register file as LOCAL_ONLY before upload."""
        relative_path = str(Path(file_path).relative_to(relative_to))

        mutation = """
        mutation CreateFileMetadata($input: CreateFileMetadataInput!) {
          createFileMetadata(input: $input) {
            corpusId
            filePath
            status
          }
        }
        """
        variables = {
            'input': {
                'corpusId': self.corpus_name,
                'filePath': relative_path,
                'status': 'LOCAL_ONLY',
            }
        }
        return self._execute_graphql(mutation, variables)

    def upload_file(
        self,
        local_path: Path,
        relative_to: Path
    ) -> Dict[str, Any]:
        """Upload file to S3 (direct mirror of local structure)."""
        relative_path = str(local_path.relative_to(relative_to))
        s3_key = f'{self.corpus_name}/{relative_path}'

        # Update status to UPLOADING
        mutation = """
        mutation UpdateFileMetadata($input: UpdateFileMetadataInput!) {
          updateFileMetadata(input: $input) {
            corpusId
            filePath
            status
          }
        }
        """
        variables = {
            'input': {
                'corpusId': self.corpus_name,
                'filePath': relative_path,
                'status': 'UPLOADING',
            }
        }
        self._execute_graphql(mutation, variables)

        # Upload to S3 (this will trigger Lambda → AVAILABLE)
        with open(local_path, 'rb') as f:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=f
            )

        return {'s3Key': s3_key}

    def sync_catalog(self, catalog_path: Path, force: bool = False) -> 'SyncResult':
        """Sync catalog.json to Amplify (idempotent)."""
        from biblicus.models import CorpusCatalog
        import hashlib
        import json

        # 1. Load and hash catalog
        catalog = CorpusCatalog.load(catalog_path)
        catalog_hash = self._compute_catalog_hash(catalog)

        # 2. Check if changed (idempotency)
        try:
            metadata = self._get_catalog_metadata()
            if not force and metadata and metadata.get('catalogHash') == catalog_hash:
                return SyncResult(skipped=True, reason="Catalog unchanged", hash=catalog_hash)
        except:
            metadata = None

        # 3. Choose sync strategy
        if len(catalog.items) < 100 or force:
            result = self._full_replacement_sync(catalog, catalog_hash)
        else:
            result = self._incremental_sync(catalog, metadata, catalog_hash)

        # 4. Update metadata
        self._sync_catalog_metadata(catalog, catalog_hash)

        return result

    def _compute_catalog_hash(self, catalog: 'CorpusCatalog') -> str:
        """Hash catalog excluding timestamps for idempotency."""
        import hashlib
        import json

        items_data = sorted([
            (item.id, item.sha256, item.relpath)
            for item in catalog.items
        ])
        return hashlib.sha256(json.dumps(items_data).encode()).hexdigest()

    def _get_catalog_metadata(self) -> Optional[Dict[str, Any]]:
        """Get current catalog metadata from Amplify."""
        query = """
        query GetCatalogMetadata($corpusId: ID!) {
          getCatalogMetadata(corpusId: $corpusId) {
            corpusId
            catalogHash
            itemCount
            lastSyncedAt
          }
        }
        """
        variables = {'corpusId': self.corpus_name}
        try:
            result = self._execute_graphql(query, variables)
            return result.get('getCatalogMetadata')
        except:
            return None

    def _sync_catalog_metadata(self, catalog: 'CorpusCatalog', catalog_hash: str):
        """Update catalog metadata in Amplify."""
        mutation = """
        mutation UpdateCatalogMetadata($input: UpdateCatalogMetadataInput!) {
          updateCatalogMetadata(input: $input) {
            corpusId
            catalogHash
          }
        }
        """
        variables = {
            'input': {
                'corpusId': self.corpus_name,
                'catalogHash': catalog_hash,
                'itemCount': len(catalog.items),
                'lastSyncedAt': datetime.now(timezone.utc).isoformat(),
                'schemaVersion': catalog.schema_version,
                'configurationId': catalog.configuration_id if hasattr(catalog, 'configuration_id') else None,
                'corpusUri': catalog.corpus_uri if hasattr(catalog, 'corpus_uri') else None,
            }
        }
        try:
            self._execute_graphql(mutation, variables)
        except:
            # Try create if update failed
            mutation = mutation.replace('updateCatalogMetadata', 'createCatalogMetadata')
            mutation = mutation.replace('UpdateCatalogMetadataInput', 'CreateCatalogMetadataInput')
            self._execute_graphql(mutation, variables)

    def _full_replacement_sync(self, catalog: 'CorpusCatalog', catalog_hash: str) -> 'SyncResult':
        """Replace all catalog items (for small catalogs)."""
        errors = []
        created = 0

        # Delete existing items (not implemented - Amplify will overwrite on create with same ID)

        # Create all items
        for item in catalog.items:
            try:
                self._create_catalog_item(item)
                created += 1
            except Exception as e:
                errors.append(f"Failed to sync item {item.id}: {e}")

        return SyncResult(
            skipped=False,
            created=created,
            updated=0,
            deleted=0,
            errors=errors,
            hash=catalog_hash
        )

    def _incremental_sync(self, catalog: 'CorpusCatalog', metadata: Optional[Dict], catalog_hash: str) -> 'SyncResult':
        """Sync only changed items (for large catalogs)."""
        # For MVP, just do full replacement
        # TODO: Implement proper diff logic
        return self._full_replacement_sync(catalog, catalog_hash)

    def _create_catalog_item(self, item: 'CatalogItem'):
        """Create or update a catalog item with retry."""
        mutation = """
        mutation CreateCatalogItem($input: CreateCatalogItemInput!) {
          createCatalogItem(input: $input) {
            corpusId
            itemId
          }
        }
        """

        variables = {
            'input': {
                'corpusId': self.corpus_name,
                'itemId': item.id,
                'relpath': item.relpath,
                'sha256': item.sha256,
                'bytes': item.bytes,
                'mediaType': item.media_type,
                'title': item.title if hasattr(item, 'title') else None,
                'tags': item.tags if hasattr(item, 'tags') else [],
                'metadataJson': item.metadata if hasattr(item, 'metadata') else {},
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'sourceUri': item.source_uri if hasattr(item, 'source_uri') else None,
                'hasExtraction': False,
            }
        }

        # Retry logic
        for attempt in range(3):
            try:
                self._execute_graphql(mutation, variables)
                return
            except Exception as e:
                if attempt < 2 and 'Network' in str(e):
                    time.sleep(2 ** attempt)
                    continue
                raise

    def _execute_graphql(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GraphQL mutation against AppSync."""
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,
        }

        payload = {
            'query': query,
            'variables': variables,
        }

        response = requests.post(
            self.appsync_endpoint,
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()

        result = response.json()
        if 'errors' in result:
            raise Exception(f"GraphQL errors: {result['errors']}")

        return result.get('data', {})
```

#### 2.2 Integration with Extraction Module
**File**: `src/biblicus/extraction.py` (modifications)

```python
from biblicus.sync.amplify_publisher import AmplifyPublisher

class ExtractionRun:
    def __init__(self, corpus: Corpus, config: ExtractionConfig):
        self.corpus = corpus
        self.config = config
        self.publisher = None

        # Initialize Amplify publisher if configured
        if os.getenv('AMPLIFY_APPSYNC_ENDPOINT'):
            self.publisher = AmplifyPublisher(corpus.name)
            self.publisher.create_corpus()

    def run(self):
        # Use Biblicus's existing content-addressable snapshot ID
        from biblicus.extraction import generate_snapshot_id
        snapshot_id = generate_snapshot_id(self.config, self.corpus.catalog)
        total_items = len(list(self.corpus.raw_files))

        # Publish intent event
        if self.publisher:
            self.publisher.start_snapshot(
                snapshot_id=snapshot_id,
                snapshot_type='EXTRACTION',
                total_items=total_items
            )

        completed = 0
        for file_path in self.corpus.raw_files:
            # Extract file
            result = self._extract_file(file_path)

            # Register and upload
            if self.publisher:
                self.publisher.register_file(result.output_path, self.corpus.root)
                self.publisher.upload_file(result.output_path, self.corpus.root)

            completed += 1

            # Update progress every 10 items
            if self.publisher and completed % 10 == 0:
                self.publisher.update_snapshot_progress(snapshot_id, completed)

        # Complete snapshot
        if self.publisher:
            self.publisher.complete_snapshot(snapshot_id, total_items)

            # Auto-sync catalog if enabled
            if os.getenv('AMPLIFY_AUTO_SYNC_CATALOG', 'true').lower() == 'true':
                try:
                    click.echo('Syncing catalog to Amplify...')
                    result = self.publisher.sync_catalog(self.corpus.catalog_path, force=False)
                    if result.skipped:
                        click.echo(f'✓ Catalog unchanged')
                    else:
                        click.echo(f'✓ Synced {result.created} items')
                except Exception as e:
                    # Don't fail extraction if sync fails
                    click.echo(f'⚠ Catalog sync failed: {e}', err=True)
```

#### 2.3 CLI Configuration Command
**File**: `src/biblicus/cli.py` (add command)

```python
@click.group()
def configure():
    """Configure Biblicus integrations."""
    pass

@configure.command()
@click.option('--endpoint', required=True, help='AppSync GraphQL endpoint')
@click.option('--api-key', required=True, help='AppSync API key')
@click.option('--bucket', required=True, help='S3 bucket name')
@click.option('--region', default='us-east-1', help='AWS region')
def amplify(endpoint, api_key, bucket, region):
    """Configure AWS Amplify integration."""
    config = {
        'AMPLIFY_APPSYNC_ENDPOINT': endpoint,
        'AMPLIFY_API_KEY': api_key,
        'AMPLIFY_S3_BUCKET': bucket,
        'AWS_REGION': region,
    }

    # Save to ~/.biblicus/amplify.env
    config_dir = Path.home() / '.biblicus'
    config_dir.mkdir(exist_ok=True)

    env_file = config_dir / 'amplify.env'
    with open(env_file, 'w') as f:
        for key, value in config.items():
            f.write(f'{key}={value}\n')

    click.echo(f'✓ Amplify configuration saved to {env_file}')
    click.echo('  Add this to your shell profile:')
    click.echo(f'  export $(cat {env_file} | xargs)')
```

#### 2.4 CLI Sync Commands
**File**: `src/biblicus/cli.py` (add new command group)

```python
@cli.group()
def sync():
    """Sync corpus data to Amplify."""
    pass

@sync.command()
@click.argument('corpus_path', type=click.Path(exists=True))
@click.option('--force', is_flag=True, help='Force full sync even if unchanged')
@click.option('--items', multiple=True, help='Sync specific item IDs only')
@click.option('--quiet', is_flag=True, help='Suppress progress output')
def catalog(corpus_path, force, items, quiet):
    """Sync catalog.json to Amplify."""
    from biblicus.corpus import Corpus
    from biblicus.sync.amplify_publisher import AmplifyPublisher

    corpus = Corpus.load(corpus_path)
    publisher = AmplifyPublisher(corpus.name)

    if not quiet:
        click.echo(f'Syncing catalog for {corpus.name}...')

    try:
        result = publisher.sync_catalog(corpus.catalog_path, force=force)

        if result.skipped:
            if not quiet:
                click.echo(f'✓ Catalog unchanged (hash: {result.hash[:8]}...)')
        else:
            if not quiet:
                click.echo(f'✓ Synced: {result.created} created, {result.updated} updated, {result.deleted} deleted')

        if result.errors:
            click.echo(f'⚠ {len(result.errors)} errors occurred:', err=True)
            for error in result.errors[:5]:
                click.echo(f'  - {error}', err=True)
            if len(result.errors) > 5:
                click.echo(f'  ... and {len(result.errors) - 5} more', err=True)

    except Exception as e:
        click.echo(f'✗ Sync failed: {e}', err=True)
        raise click.Abort()

@sync.command()
@click.argument('corpus_path', type=click.Path(exists=True))
@click.option('--interval', default=2, help='Check interval in seconds')
def watch(corpus_path, interval):
    """Watch catalog.json and auto-sync on changes."""
    from biblicus.corpus import Corpus
    from biblicus.sync.amplify_publisher import AmplifyPublisher
    import time
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    corpus = Corpus.load(corpus_path)
    catalog_path = corpus.catalog_path
    publisher = AmplifyPublisher(corpus.name)

    class CatalogSyncHandler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path == str(catalog_path):
                click.echo(f'[{datetime.now().strftime("%H:%M:%S")}] Catalog changed, syncing...')
                try:
                    result = publisher.sync_catalog(catalog_path, force=False)
                    if result.skipped:
                        click.echo(f'  ✓ Unchanged')
                    else:
                        click.echo(f'  ✓ Synced: {result.created}c {result.updated}u {result.deleted}d')
                except Exception as e:
                    click.echo(f'  ✗ Failed: {e}', err=True)

    observer = Observer()
    observer.schedule(CatalogSyncHandler(), path=str(catalog_path.parent), recursive=False)
    observer.start()

    click.echo(f'Watching {catalog_path} for changes... (Ctrl+C to stop)')
    try:
        while True:
            time.sleep(interval)
    except KeyboardInterrupt:
        observer.stop()
        click.echo('\nStopped watching')
    observer.join()
```

#### 2.3 Real-Time Snapshot Updates

The dashboard uses Amplify Gen 2's built-in real-time subscriptions to display extraction progress without polling.

**Key Pattern**: State changes via table records, not arbitrary signals. This pattern comes "for free" from Amplify Gen 2.

**Backend Implementation** (`src/biblicus/sync/amplify_publisher.py`):

Already implemented methods:
- `start_snapshot(snapshot_id, snapshot_type, total_items)` - Creates Snapshot with `status='RUNNING'`
- `update_snapshot_progress(snapshot_id, completed_items)` - Updates `completedItems` field
- `complete_snapshot(snapshot_id, total_items, error_message=None)` - Marks `status='COMPLETED'` or `FAILED'`

Pattern:
1. Create Snapshot record with `status='RUNNING'`, `completedItems=0`
2. Update `completedItems` incrementally as extraction progresses
3. Update `status='COMPLETED'` or `FAILED'` when done

No WebSocket code needed in Python—just HTTP GraphQL mutations. AppSync automatically publishes changes to subscribers.

**Frontend Implementation** (`apps/dashboard/src/pages/CorpusDashboardPage.tsx`):

Uses `observeQuery()` to subscribe to Snapshot table changes:

```typescript
useEffect(() => {
  const subscription = client.models.Snapshot.observeQuery({
    filter: { corpusId: { eq: corpusName } }
  }).subscribe({
    next: ({ items }) => {
      setSnapshots(items); // Automatic re-render on create/update/delete
    },
    error: (err) => {
      console.error('Subscription error:', err);
    }
  });

  return () => subscription.unsubscribe();
}, [corpusName]);
```

Automatically receives:
- `onCreate`: New snapshot appears when CLI calls `start_snapshot()`
- `onUpdate`: Progress bar animates as CLI calls `update_snapshot_progress()`
- `onUpdate`: Status changes when CLI calls `complete_snapshot()`

**Test Script** (`scripts/test_snapshot_realtime.py`):

Simulates extraction with 0-100% progress updates:

```python
publisher = AmplifyPublisher('Alfa')
snapshot_id = f"test-extraction-{int(time.time())}"

# Create snapshot (dashboard sees it appear within 1s)
publisher.start_snapshot(snapshot_id, 'EXTRACTION', total_items=100)

# Update progress every 2 seconds (dashboard progress bar animates)
for i in range(0, 101, 20):
    publisher.update_snapshot_progress(snapshot_id, completed_items=i)
    time.sleep(2)

# Complete (dashboard shows completion indicator)
publisher.complete_snapshot(snapshot_id, total_items=100)
```

Run with:
```bash
# Terminal 1: Watch dashboard
cd apps/dashboard && npm run dev

# Terminal 2: Simulate extraction
python scripts/test_snapshot_realtime.py
```

Expected: Snapshot appears, progress bar animates 0→100%, status changes to COMPLETED.

**Key Design Decision**: No custom WebSocket infrastructure. Amplify Gen 2 provides real-time updates automatically via AppSync subscriptions on DynamoDB changes.

See [Real-Time Subscriptions Guide](realtime-subscriptions.md) for detailed documentation.

### Phase 3: Vite + React Frontend

#### 3.1 Project Setup
```bash
npm create vite@latest biblicus-viewer -- --template react-ts
cd biblicus-viewer
npm install
npm install aws-amplify gsap @gsap/react react-router-dom
npm install -D @aws-amplify/backend @aws-amplify/backend-cli tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

#### 3.2 Amplify Client Configuration
**File**: `lib/amplify-client.ts`

```typescript
import { generateClient } from 'aws-amplify/data';
import type { Schema } from '@/amplify/data/resource';

export const client = generateClient<Schema>();

export type Corpus = Schema['Corpus']['type'];
export type Snapshot = Schema['Snapshot']['type'];
export type FileMetadata = Schema['FileMetadata']['type'];
export type CatalogMetadata = Schema['CatalogMetadata']['type'];
export type CatalogItem = Schema['CatalogItem']['type'];
```

#### 3.3 App Entry Point with Amplify
**File**: `src/main.tsx`

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { Amplify } from 'aws-amplify';
import { BrowserRouter } from 'react-router-dom';
import outputs from '../amplify_outputs.json';
import App from './App';
import './index.css';

Amplify.configure(outputs);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
```

**File**: `src/App.tsx`

```typescript
import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import CorpusDashboardPage from './pages/CorpusDashboardPage';
import ExtractedSnapshotPage from './pages/ExtractedSnapshotPage';
import ExtractedFilePage from './pages/ExtractedFilePage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/corpus/:corpusName" element={<CorpusDashboardPage />} />
      <Route path="/corpus/:corpusName/extracted/:snapshotId" element={<ExtractedSnapshotPage />} />
      <Route path="/corpus/:corpusName/extracted/:snapshotId/*" element={<ExtractedFilePage />} />
    </Routes>
  );
}
```

#### 3.4 Corpus List Page
**File**: `src/pages/HomePage.tsx`

```typescript
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { client, type Corpus } from '../lib/amplify-client';

export default function HomePage() {
  const [corpuses, setCorpuses] = useState<Corpus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadCorpuses() {
      const { data } = await client.models.Corpus.list();
      setCorpuses(data);
      setLoading(false);
    }
    loadCorpuses();
  }, []);

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <div className="animate-pulse">Loading corpuses...</div>
      </main>
    );
  }

  return (
    <main className="container mx-auto p-8">
      <h1 className="text-4xl font-bold mb-8">Biblicus Corpuses</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {corpuses.map((corpus) => (
          <Link
            key={corpus.name}
            to={`/corpus/${corpus.name}`}
            className="p-6 border rounded-lg hover:shadow-lg transition"
          >
            <h2 className="text-2xl font-semibold mb-2">{corpus.name}</h2>
            <p className="text-gray-600">Status: {corpus.status}</p>
            {corpus.lastActivity && (
              <p className="text-sm text-gray-500 mt-2">
                Last activity: {new Date(corpus.lastActivity).toLocaleString()}
              </p>
            )}
          </Link>
        ))}
      </div>
    </main>
  );
}
```

#### 3.5 Corpus Dashboard with Real-time Updates
**File**: `src/pages/CorpusDashboardPage.tsx`

```typescript
import { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { client, type Snapshot } from '../lib/amplify-client';
import { ProgressCard } from '../components/dashboard/ProgressCard';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(useGSAP);

export default function CorpusDashboardPage() {
  const { corpusName } = useParams<{ corpusName: string }>();
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  // Subscribe to real-time updates
  useEffect(() => {
    if (!corpusName) return;

    const subscription = client.models.Snapshot.observeQuery({
      filter: { corpusId: { eq: corpusName } },
    }).subscribe({
      next: ({ items }) => {
        setSnapshots(items);
        setLoading(false);
      },
    });

    return () => subscription.unsubscribe();
  }, [corpusName]);

  // Animate new snapshots
  useGSAP(() => {
    if (containerRef.current) {
      gsap.fromTo(
        containerRef.current.children,
        { opacity: 0, y: 20 },
        {
          opacity: 1,
          y: 0,
          duration: 0.5,
          stagger: 0.1,
          ease: 'power2.out',
        }
      );
    }
  }, [snapshots.length]);

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <div className="animate-pulse">Loading dashboard...</div>
      </main>
    );
  }

  return (
    <main className="container mx-auto p-8">
      <h1 className="text-4xl font-bold mb-8">{corpusName}</h1>

      <div ref={containerRef} className="space-y-6">
        {snapshots.map((snapshot) => (
          <ProgressCard
            key={`${snapshot.corpusId}-${snapshot.snapshotId}`}
            snapshot={snapshot}
          />
        ))}
      </div>
    </main>
  );
}
```

**File**: `src/components/dashboard/ProgressCard.tsx`

```typescript
import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { type Snapshot } from '../../lib/amplify-client';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

export function ProgressCard({ snapshot }: { snapshot: Snapshot }) {
  const progressRef = useRef<HTMLDivElement>(null);

  const progress = snapshot.totalItems
    ? (snapshot.completedItems / snapshot.totalItems) * 100
    : 0;

  // Animate progress bar
  useGSAP(() => {
    if (progressRef.current) {
      gsap.to(progressRef.current, {
        width: `${progress}%`,
        duration: 0.6,
        ease: 'power2.out',
      });
    }
  }, [progress]);

  const statusColors = {
    PENDING: 'bg-gray-500',
    RUNNING: 'bg-blue-500',
    COMPLETED: 'bg-green-500',
    FAILED: 'bg-red-500',
  };

  return (
    <Link
      to={`/corpus/${snapshot.corpusId}/${snapshot.type.toLowerCase()}/${snapshot.snapshotId}`}
      className="block p-6 border rounded-lg hover:shadow-lg transition"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold">
          {snapshot.type} - {snapshot.snapshotId}
        </h3>
        <span className={`px-3 py-1 rounded text-white text-sm ${statusColors[snapshot.status]}`}>
          {snapshot.status}
        </span>
      </div>

      <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          ref={progressRef}
          className="absolute inset-y-0 left-0 bg-blue-600 rounded-full"
          style={{ width: '0%' }}
        />
      </div>

      <p className="mt-2 text-sm text-gray-600">
        {snapshot.completedItems} / {snapshot.totalItems} items
      </p>

      {snapshot.errorMessage && (
        <p className="mt-2 text-sm text-red-600">{snapshot.errorMessage}</p>
      )}
    </Link>
  );
}
```

#### 3.6 Lazy Content Loading
**File**: `src/components/lazy/LazyContent.tsx`

```typescript
import { useEffect, useState } from 'react';
import { client } from '../../lib/amplify-client';
import { downloadData } from 'aws-amplify/storage';

export function LazyContent({
  corpusId,
  filePath,
}: {
  corpusId: string;
  filePath: string;
}) {
  const [status, setStatus] = useState<'loading' | 'available' | 'local_only'>('loading');
  const [content, setContent] = useState<string | null>(null);

  useEffect(() => {
    let subscription: any;

    async function loadContent() {
      // Subscribe to file metadata changes
      subscription = client.models.FileMetadata.observeQuery({
        filter: {
          corpusId: { eq: corpusId },
          filePath: { eq: filePath },
        },
      }).subscribe({
        next: async ({ items }) => {
          const file = items[0];

          if (!file) {
            setStatus('local_only');
            return;
          }

          if (file.status === 'AVAILABLE' && file.s3Key) {
            try {
              const { body } = await downloadData({
                path: file.s3Key,
              }).result;

              const text = await body.text();
              setContent(text);
              setStatus('available');
            } catch (error) {
              console.error('Failed to download:', error);
            }
          } else {
            setStatus('local_only');
          }
        },
      });
    }

    loadContent();

    return () => {
      if (subscription) {
        subscription.unsubscribe();
      }
    };
  }, [corpusId, filePath]);

  if (status === 'loading') {
    return <div className="animate-pulse">Loading...</div>;
  }

  if (status === 'local_only') {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
        <p className="text-yellow-800">
          File exists locally but hasn't been synced to cloud yet.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 bg-white rounded shadow">
      <pre className="whitespace-pre-wrap font-mono text-sm">
        {content}
      </pre>
    </div>
  );
}
```

#### 3.7 Zoom Transition Component
**File**: `src/components/dashboard/ZoomTransition.tsx`

```typescript
import { useRef, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import gsap from 'gsap';

export function ZoomTransition({
  children,
  to,
}: {
  children: ReactNode;
  to: string;
}) {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);

  const handleClick = () => {
    if (!containerRef.current) return;

    gsap.timeline()
      .to(containerRef.current, {
        scale: 1.1,
        opacity: 0,
        duration: 0.3,
        ease: 'power2.in',
      })
      .call(() => {
        navigate(to);
      });
  };

  return (
    <div
      ref={containerRef}
      onClick={handleClick}
      className="cursor-pointer transition-transform hover:scale-105"
    >
      {children}
    </div>
  );
}
```

#### 3.8 Catalog Browser Components

Update App routes to include catalog:

**File**: `src/App.tsx` (update)

```typescript
import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import CorpusDashboardPage from './pages/CorpusDashboardPage';
import CatalogBrowserPage from './pages/CatalogBrowserPage';
import CatalogItemDetailPage from './pages/CatalogItemDetailPage';
import ExtractedSnapshotPage from './pages/ExtractedSnapshotPage';
import ExtractedFilePage from './pages/ExtractedFilePage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/corpus/:corpusName" element={<CorpusDashboardPage />} />
      <Route path="/corpus/:corpusName/catalog" element={<CatalogBrowserPage />} />
      <Route path="/corpus/:corpusName/catalog/:itemId" element={<CatalogItemDetailPage />} />
      <Route path="/corpus/:corpusName/extracted/:snapshotId" element={<ExtractedSnapshotPage />} />
      <Route path="/corpus/:corpusName/extracted/:snapshotId/*" element={<ExtractedFilePage />} />
    </Routes>
  );
}
```

**CatalogBrowserPage with filtering and real-time updates:**

**File**: `src/pages/CatalogBrowserPage.tsx`

```typescript
import { useEffect, useState, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { client, type CatalogItem } from '../lib/amplify-client';
import { CatalogItemCard } from '../components/catalog/CatalogItemCard';
import { CatalogFilters } from '../components/catalog/CatalogFilters';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(useGSAP);

export default function CatalogBrowserPage() {
  const { corpusName } = useParams<{ corpusName: string }>();
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  const tag = searchParams.get('tag');
  const mediaType = searchParams.get('mediaType');
  const search = searchParams.get('search');

  useEffect(() => {
    if (!corpusName) return;

    // Build query based on filters
    const subscription = client.models.CatalogItem.observeQuery({
      filter: { corpusId: { eq: corpusName } }
    }).subscribe({
      next: ({ items: fetchedItems }) => {
        let filtered = fetchedItems;

        // Client-side filters
        if (tag) {
          filtered = filtered.filter(item => item.tags?.includes(tag));
        }
        if (mediaType) {
          filtered = filtered.filter(item => item.mediaType === mediaType);
        }
        if (search) {
          const searchLower = search.toLowerCase();
          filtered = filtered.filter(item =>
            item.title?.toLowerCase().includes(searchLower) ||
            item.relpath.toLowerCase().includes(searchLower)
          );
        }

        setItems(filtered);
        setLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, [corpusName, tag, mediaType, search]);

  // Animate items on load/filter change
  useGSAP(() => {
    if (containerRef.current && items.length > 0) {
      gsap.fromTo(
        containerRef.current.children,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, stagger: 0.05, duration: 0.5 }
      );
    }
  }, [items.length, tag, mediaType, search]);

  if (loading) {
    return <div className="p-8 animate-pulse">Loading catalog...</div>;
  }

  return (
    <main className="container mx-auto p-8">
      <h1 className="text-4xl font-bold mb-8">{corpusName} Catalog</h1>

      <CatalogFilters corpusName={corpusName} />

      <div ref={containerRef} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
        {items.map(item => (
          <CatalogItemCard key={item.itemId} item={item} />
        ))}
      </div>

      {items.length === 0 && (
        <p className="text-gray-500 text-center mt-8">No items found</p>
      )}
    </main>
  );
}
```

**File**: `src/components/catalog/CatalogItemCard.tsx`

```typescript
import { Link } from 'react-router-dom';
import { type CatalogItem } from '../../lib/amplify-client';

export function CatalogItemCard({ item }: { item: CatalogItem }) {
  return (
    <Link
      to={`/corpus/${item.corpusId}/catalog/${item.itemId}`}
      className="p-6 border rounded-lg hover:shadow-lg transition-all duration-200"
    >
      <h3 className="text-xl font-semibold mb-2 line-clamp-2">
        {item.title || item.relpath}
      </h3>

      <div className="flex gap-2 mb-2 flex-wrap">
        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
          {item.mediaType}
        </span>
        {item.hasExtraction && (
          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
            Extracted
          </span>
        )}
      </div>

      {item.tags && item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {item.tags.slice(0, 3).map(tag => (
            <span key={tag} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
              {tag}
            </span>
          ))}
          {item.tags.length > 3 && (
            <span className="px-2 py-1 text-gray-500 text-xs">
              +{item.tags.length - 3} more
            </span>
          )}
        </div>
      )}

      <p className="text-sm text-gray-500">
        {(item.bytes / 1024).toFixed(1)} KB
      </p>
    </Link>
  );
}
```

**File**: `src/components/catalog/CatalogFilters.tsx`

```typescript
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

export function CatalogFilters({ corpusName }: { corpusName: string }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams(searchParams);
    if (searchInput) {
      params.set('search', searchInput);
    } else {
      params.delete('search');
    }
    setSearchParams(params);
  };

  const clearFilters = () => {
    setSearchParams({});
    setSearchInput('');
  };

  const activeFilters = Array.from(searchParams.entries());

  return (
    <div className="space-y-4">
      <form onSubmit={handleSearchSubmit} className="flex gap-2">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by title or path..."
          className="flex-1 px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button type="submit" className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Search
        </button>
      </form>

      {activeFilters.length > 0 && (
        <div className="flex gap-2 items-center flex-wrap">
          <span className="text-sm text-gray-600">Active filters:</span>
          {activeFilters.map(([key, value]) => (
            <span key={key} className="px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded">
              {key}: {value}
            </span>
          ))}
          <button
            onClick={clearFilters}
            className="px-3 py-1 text-sm text-red-600 hover:underline"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
```

**File**: `src/pages/CatalogItemDetailPage.tsx`

```typescript
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { client, type CatalogItem, type FileMetadata } from '../lib/amplify-client';

export default function CatalogItemDetailPage() {
  const { corpusName, itemId } = useParams<{ corpusName: string; itemId: string }>();
  const [item, setItem] = useState<CatalogItem | null>(null);
  const [extractions, setExtractions] = useState<FileMetadata[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!corpusName || !itemId) return;

    // Load catalog item
    client.models.CatalogItem.get({ corpusId: corpusName, itemId }).then(({ data }) => {
      setItem(data);
      setLoading(false);
    });

    // Load extractions for this item
    client.models.FileMetadata.list({
      filter: {
        corpusId: { eq: corpusName },
        filePath: { contains: itemId }
      }
    }).then(({ data }) => {
      setExtractions(data);
    });
  }, [corpusName, itemId]);

  if (loading || !item) {
    return <div className="p-8 animate-pulse">Loading item...</div>;
  }

  return (
    <main className="container mx-auto p-8">
      <div className="mb-4">
        <Link to={`/corpus/${corpusName}/catalog`} className="text-blue-600 hover:underline">
          ← Back to catalog
        </Link>
      </div>

      <h1 className="text-4xl font-bold mb-2">{item.title || item.relpath}</h1>

      <div className="flex gap-2 mb-6 flex-wrap">
        <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded">
          {item.mediaType}
        </span>
        {item.tags?.map(tag => (
          <span key={tag} className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded">
            {tag}
          </span>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h2 className="text-2xl font-semibold mb-4">Metadata</h2>
          <dl className="space-y-2">
            <dt className="font-semibold">Path:</dt>
            <dd className="text-gray-600 font-mono text-sm">{item.relpath}</dd>

            <dt className="font-semibold">SHA256:</dt>
            <dd className="font-mono text-xs text-gray-600 break-all">{item.sha256}</dd>

            <dt className="font-semibold">Size:</dt>
            <dd className="text-gray-600">{(item.bytes / 1024).toFixed(1)} KB</dd>

            {item.sourceUri && (
              <>
                <dt className="font-semibold">Source:</dt>
                <dd className="text-gray-600">{item.sourceUri}</dd>
              </>
            )}
          </dl>

          {item.metadataJson && Object.keys(item.metadataJson).length > 0 && (
            <div className="mt-6">
              <h3 className="text-xl font-semibold mb-2">Custom Metadata</h3>
              <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
                {JSON.stringify(item.metadataJson, null, 2)}
              </pre>
            </div>
          )}
        </div>

        <div>
          <h2 className="text-2xl font-semibold mb-4">Extractions</h2>
          {extractions.length === 0 ? (
            <p className="text-gray-500">No extractions yet</p>
          ) : (
            <ul className="space-y-2">
              {extractions.map(extraction => (
                <li key={extraction.filePath} className="p-4 border rounded">
                  <Link
                    to={`/corpus/${corpusName}/extracted/${extraction.filePath}`}
                    className="text-blue-600 hover:underline font-mono text-sm"
                  >
                    {extraction.filePath}
                  </Link>
                  <div className="flex gap-2 mt-2">
                    <span className={`text-xs px-2 py-1 rounded ${
                      extraction.status === 'AVAILABLE' ? 'bg-green-100 text-green-800' :
                      extraction.status === 'UPLOADING' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {extraction.status}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </main>
  );
}
```

### Phase 4: Deployment

#### 4.1 Deploy Amplify Backend
```bash
npx ampx sandbox
# Test in sandbox mode first

# Deploy to production
npx ampx pipeline-deploy --branch main --app-id <your-app-id>
```

#### 4.2 Export Configuration for Python
After deployment, export the configuration:

```bash
# amplify_outputs.json contains:
# - AppSync endpoint
# - S3 bucket name
# - Region
# - API key (for public access)

# Create Python configuration
cat amplify_outputs.json | jq -r '
  "export AMPLIFY_APPSYNC_ENDPOINT=\(.data.url)",
  "export AMPLIFY_API_KEY=\(.data.api_key)",
  "export AMPLIFY_S3_BUCKET=\(.storage.bucket_name)",
  "export AWS_REGION=\(.data.aws_region)"
' > amplify-python.env
```

Users run:
```bash
source amplify-python.env
export AMPLIFY_USER_ID=$(aws cognito-idp admin-get-user --user-pool-id <pool-id> --username <email> | jq -r .Username)
biblicus configure amplify \
  --endpoint $AMPLIFY_APPSYNC_ENDPOINT \
  --api-key $AMPLIFY_API_KEY \
  --bucket $AMPLIFY_S3_BUCKET \
  --user-id $AMPLIFY_USER_ID \
  --region $AWS_REGION
```

#### 4.3 Deploy Frontend
Amplify automatically deploys Vite apps:

1. Connect Git repository in Amplify Console
2. Configure build settings:
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - npm ci
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: dist
       files:
         - '**/*'
     cache:
       paths:
         - node_modules/**/*
   ```
3. Add redirects for client-side routing in `public/_redirects`:
   ```
   /*    /index.html   200
   ```
4. Each push to `main` triggers deployment

## URL Structure

```
/                                              → Corpus list
/corpus/:corpusName                            → Dashboard (all snapshots)
/corpus/:corpusName/catalog                    → Catalog browser
/corpus/:corpusName/catalog/:itemId            → Catalog item detail + extractions
/corpus/:corpusName/catalog?tag=wikipedia      → Filtered catalog view
/corpus/:corpusName/catalog?mediaType=pdf      → Media type filter
/corpus/:corpusName/catalog?search=query       → Search catalog
/corpus/:corpusName/extracted/:snapshotId      → Extraction snapshot detail
/corpus/:corpusName/extracted/:snapshotId/:file → Individual file view
/corpus/:corpusName/analysis/:runId            → Analysis run detail
/corpus/:corpusName/retrieval/:snapshotId      → Retrieval snapshot detail
/corpus/:corpusName/graph/:snapshotId          → Graph snapshot detail
```

All URLs are:
- Deep-linkable (shareable with stakeholders)
- Bookmarkable
- Support client-side routing with React Router
- Real-time subscriptions for updates

## Animation Patterns

### Dashboard Entry
```typescript
gsap.fromTo(cards,
  { opacity: 0, y: 20 },
  { opacity: 1, y: 0, stagger: 0.1, duration: 0.5 }
);
```

### Progress Updates
```typescript
gsap.to(progressBar, {
  width: `${percentage}%`,
  duration: 0.6,
  ease: 'power2.out'
});
```

### Zoom Transitions (Dashboard → Detail)
```typescript
gsap.timeline()
  .to(card, { scale: 1.1, opacity: 0, duration: 0.3 })
  .call(() => router.push(detailUrl))
  .to(detailView, { scale: 1, opacity: 1, duration: 0.4 });
```

### New Item Appearance
```typescript
gsap.fromTo(newCard,
  { scale: 0, opacity: 0 },
  { scale: 1, opacity: 1, duration: 0.5, ease: 'back.out(1.7)' }
);
```

## Testing Strategy

### 1. Local Development
```bash
# Terminal 1: Amplify sandbox
cd biblicus-viewer
npx ampx sandbox

# Terminal 2: Next.js dev server
npm run dev

# Terminal 3: Python CLI with local corpus
cd ../Biblicus
source ../biblicus-viewer/amplify-python.env
export AMPLIFY_USER_ID=test-user
biblicus extract corpus-test --config configs/baseline-ocr.yaml
```

### 2. Real-time Validation
- Start extraction run
- Watch dashboard update in real-time
- Verify LOCAL_ONLY → UPLOADING → AVAILABLE flow
- Click through to detail views
- Verify animations are smooth

### 3. Deep Link Testing
- Copy any URL from browser
- Open in new incognito window
- Verify context loads correctly
- Test 404 behavior for not-yet-synced files

## Catalog Integration Strategy

### Why DynamoDB Records Instead of Just S3 Files?

The catalog integration stores catalog items as DynamoDB records (via Amplify Data models) rather than just uploading catalog.json to S3. This design choice provides:

1. **Fast Filtering**: GSI indexes enable efficient queries by tag, media type, or extraction status without downloading the entire catalog
2. **Real-time Subscriptions**: Frontend can subscribe to catalog changes via AppSync and see updates instantly
3. **Pagination**: Built-in support for large catalogs (1000+ items) without loading everything at once
4. **No Parse Overhead**: Items are already structured data, no need to download and parse JSON for every view

### Idempotency via Content Hashing

Catalog sync is idempotent through content-addressable hashing:

- Compute hash of catalog items (id, sha256, relpath) excluding timestamps
- Compare with stored hash in CatalogMetadata table
- Skip sync if hash matches (fast no-op, typical for unchanged catalogs)
- Only sync changed items in large catalogs (>100 items)

This ensures:
- Safe to run repeatedly
- Minimal network/compute overhead
- No duplicate records
- Efficient syncs even for large catalogs

### Sync Strategies

**Small Catalogs (<100 items): Full Replacement**
- Delete all existing items (overwrite on create with same ID)
- Create all catalog items fresh
- Simple, fast, and sufficient for most use cases

**Large Catalogs (>100 items): Incremental Diff** (future enhancement)
- Query existing items from DynamoDB
- Diff by sha256 hash
- Create/update/delete only changed items
- More efficient for frequent syncs of large catalogs

**Auto-sync: After Ingest/Extraction**
- Configurable via `AMPLIFY_AUTO_SYNC_CATALOG` environment variable
- Defaults to enabled
- Non-blocking (errors don't fail extraction)
- Keeps viewer in sync automatically

**Manual Sync: CLI Commands**
- `biblicus sync catalog ./corpora/wiki_demo` - One-time sync
- `biblicus sync catalog --force` - Force full sync even if unchanged
- `biblicus sync watch ./corpora/wiki_demo` - Watch for changes and auto-sync

### Cost Estimates

DynamoDB costs for typical usage:

**1000-item catalog, 10 syncs/day:**
- Storage: $0.00025/month (1KB per item × 1000 items × $0.25/GB)
- Writes: $0.06/month (full sync) or $0.006/month (incremental with 10% changes)
- Reads: $0.02/month (frontend queries)
- **Total: $0.02-0.10/month**

**5000-item catalog, 20 syncs/day:**
- Storage: $0.00125/month
- Writes: $0.30/month (full sync) or $0.03/month (incremental)
- Reads: $0.10/month
- **Total: $0.10-0.50/month**

These costs are negligible compared to S3, Lambda, and AppSync costs. For reference, a single coffee costs more than a month of catalog sync for most users.

### S3 Path Mapping

Biblicus corpora are mirrored directly to S3 without user partitioning:

**Local Structure:**
```
/path/to/corpora/
  wiki_demo/
    metadata/
      catalog.json
      snapshots/extraction/...
    raw/
      document1.pdf
    extracted/
      text/document1.txt
```

**S3 Structure (Direct Mirror):**
```
s3://biblicus-bucket/
  wiki_demo/
    metadata/
      catalog.json
      snapshots/extraction/...
    raw/
      document1.pdf
    extracted/
      text/document1.txt
```

No `/{userId}/` prefix - each corpus is a top-level folder in the bucket. This simplifies:
- S3 key parsing in Lambda functions
- File path mapping between local and cloud
- Debugging and manual S3 browsing

Access control is handled by Amplify Storage rules, not path-based isolation.

### Content-Addressable Snapshot IDs

Biblicus uses content-addressable snapshot IDs based on configuration and catalog:

```python
snapshot_id = hash_text(f"{configuration_id}:{catalog.generated_at}")
```

This means:
- Same config + same catalog = same snapshot ID
- Deterministic and reproducible
- Enables idempotent reruns
- Links extractions to source state

The viewer uses these same IDs, maintaining consistency between CLI and web app.

## Success Criteria

1. **Real-time Updates**: Dashboard reflects extraction progress within 1 second of Python CLI publishing event
2. **Lazy Loading**: Files marked LOCAL_ONLY show appropriate UI, then update when AVAILABLE
3. **Smooth Animations**: All transitions use GSAP with no jank (60fps)
4. **Deep Linking**: All URLs work when shared with stakeholders
5. **Zero Custom Infrastructure**: 100% Amplify Gen 2, no custom AppSync schemas or Lambda functions (except S3 event handler)
6. **Type Safety**: Full TypeScript coverage with auto-generated types from Amplify schema

## Architecture Decisions

### Why Amplify Gen 2?
- Provides GraphQL, DynamoDB, real-time subscriptions, S3, Cognito out of the box
- Auto-generates TypeScript types from schema
- Built-in authorization rules
- No need to write custom AppSync schemas or resolvers
- Integrated hosting for Next.js with SSR

### Why Vite over Next.js?
- Faster dev server with instant HMR
- Simpler architecture (pure SPA, no SSR complexity)
- Amplify supports Vite hosting out of the box
- Smaller bundle size
- Client-side routing with React Router is sufficient for this use case
- Real-time subscriptions handle all dynamic data (no need for SSR)

### Why Two-Phase Events?
- **Intent phase**: Instant feedback to user (extraction started!)
- **Availability phase**: Content ready to view in browser
- Solves the "sync lag" problem - users see activity immediately even if S3 upload takes time

### Why GSAP?
- Industry standard for web animations
- Smooth 60fps performance
- Declarative API with timelines
- Works well with React refs
- Better than CSS animations for complex sequences

## Next Steps

1. Initialize Amplify project
2. Implement data schema
3. Create S3 event handler Lambda
4. Build Python CLI integration
5. Create Next.js frontend
6. Test end-to-end with real corpus
7. Deploy to production
8. Generate Python configuration export
9. Document setup for users
