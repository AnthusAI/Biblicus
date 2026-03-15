# Biblicus Corpus Viewer

Real-time web interface for viewing and managing Biblicus corpus data, powered by AWS Amplify Gen 2.

## Architecture

- **Frontend**: Vite + React + TypeScript with GSAP animations
- **Backend**: AWS Amplify Gen 2 (AppSync GraphQL + DynamoDB + S3 + Cognito)
- **Python Integration**: AmplifyPublisher module for CLI/automation

## Setup

### 1. Deploy Amplify Backend

First, set up the Amplify CLI and deploy to your AWS account:

```bash
# From Biblicus project root
cd apps/dashboard
npm install

# Deploy to production (one-time setup)
npx ampx pipeline-deploy --branch main --app-id YOUR_AMPLIFY_APP_ID
```

This will:
- Deploy Amplify resources to your AWS account
- Generate `amplify_outputs.json` with connection details
- Set up the production environment

After deployment, the Amplify console will show your:
- AppSync GraphQL endpoint
- API key
- S3 bucket name
- Cognito user pool details

Copy these values for the next step.

### 2. Configure Python CLI

```bash
# From Biblicus project root
python scripts/configure_amplify.py \
  --endpoint https://YOUR_APPSYNC_ENDPOINT.appsync-api.us-east-1.amazonaws.com/graphql \
  --api-key YOUR_API_KEY \
  --bucket YOUR_S3_BUCKET_NAME \
  --region us-east-1
```

This saves configuration to `~/.biblicus/amplify.env`.

### 3. Run Frontend

```bash
# From Biblicus project root
cd apps/dashboard
npm run dev
```

Open http://localhost:5173

## Usage

### Syncing Catalog

Manual sync:
```bash
python scripts/sync_catalog.py ./corpora/your_corpus
```

Force full sync:
```bash
python scripts/sync_catalog.py ./corpora/your_corpus --force
```

Auto-sync after extraction:
```bash
export AMPLIFY_AUTO_SYNC_CATALOG=true
# Now all extractions will auto-sync catalog
```

### Frontend Routes

- `/` - All corpora
- `/corpus/:name` - Corpus dashboard with snapshots
- `/corpus/:name/catalog` - Browse catalog items
- `/corpus/:name/catalog/:itemId` - Item detail + extractions

## Data Models

### Amplify Data Schema

**Corpus**: Top-level corpus metadata
- `name` (ID), `description`, `createdAt`, `updatedAt`

**Snapshot**: Extraction/analysis snapshots
- `corpusId`, `snapshotId`, `snapshotType`, `status`, `totalItems`, `processedItems`

**FileMetadata**: Uploaded file tracking
- `corpusId`, `filePath`, `status`, `s3Key`, `size`, `uploadedAt`

**CatalogMetadata**: Catalog sync metadata
- `corpusId`, `catalogHash`, `itemCount`, `lastSyncedAt`

**CatalogItem**: Individual catalog items
- `corpusId`, `itemId`, `relpath`, `sha256`, `bytes`, `mediaType`, `title`, `tags`
- GSI indexes for filtering by `mediaType`, `tags`, `hasExtraction`

### S3 Structure

Direct mirror of local corpus structure:
```
s3://bucket/
  corpus-name/
    catalog.json
    metadata/
    extracted/
    indexed/
```

## Development

### Amplify Sandbox

The sandbox runs locally and deploys to your AWS account:
```bash
npx ampx sandbox
```

Press Ctrl+C to tear down resources.

### Frontend Dev Server

```bash
npm run dev
```

Hot reload enabled. Changes to Amplify schema require sandbox restart.

### Python Development

The AmplifyPublisher module is in `src/biblicus/sync/amplify_publisher.py`. Key methods:

- `sync_catalog()` - Idempotent catalog sync with hash-based skip
- `upload_file()` - Direct S3 upload with FileMetadata creation
- `start_snapshot()` - Create snapshot intent record
- `complete_snapshot()` - Mark snapshot complete

## Deployment

### Production Deployment

1. Deploy Amplify backend:
```bash
npx ampx sandbox delete  # Clean up dev resources
npx ampx pipeline-deploy --branch main
```

2. Build frontend:
```bash
npm run build
```

3. Deploy frontend to S3 + CloudFront or Amplify Hosting.

### Environment Variables

Python CLI reads from `~/.biblicus/amplify.env`:
- `AMPLIFY_APPSYNC_ENDPOINT`
- `AMPLIFY_API_KEY`
- `AMPLIFY_S3_BUCKET`
- `AWS_REGION`
- `AMPLIFY_AUTO_SYNC_CATALOG` (optional, default: false)

## Architecture Decisions

### Why DynamoDB Catalog Records?

Instead of just parsing `catalog.json` from S3:
- Fast filtering by tags/media type (via GSI queries)
- Real-time subscriptions for catalog changes
- No need to download/parse entire file for every view
- Pagination support for large catalogs (1000+ items)

### Idempotent Catalog Sync

- Hash catalog content (excluding timestamps)
- Compare with stored hash before syncing
- Skip sync if unchanged (fast no-op)
- Only sync changed items in large catalogs

### Dual Authentication

- **Frontend**: Cognito user pools (username/password)
- **Python CLI**: API key (automation-friendly)
- Both modes supported simultaneously by AppSync

### Direct S3 Mirroring

No user partitioning or path transformation:
- Python: `corpus_name/relative_path`
- S3: `s3://bucket/corpus_name/relative_path`
- Simple, predictable, easy to debug

## Cost Estimates

Typical usage (1000-item catalog, 10 syncs/day):
- DynamoDB: ~$0.10/month
- S3: ~$1/month (10GB storage)
- AppSync: ~$0.50/month (1M requests)
- **Total**: ~$2/month

Amplify sandbox is free during development.

## Troubleshooting

### Amplify Outputs Not Found

Run `npx ampx sandbox` to generate `amplify_outputs.json`.

### GraphQL Errors

Check API key is valid and not expired. API keys expire after 365 days by default.

### Catalog Not Syncing

1. Check configuration: `cat ~/.biblicus/amplify.env`
2. Check AWS credentials: `aws sts get-caller-identity`
3. Run manual sync with verbose output

### Frontend Not Loading

1. Ensure Amplify sandbox is running
2. Check browser console for errors
3. Verify `amplify_outputs.json` exists and has correct values

## License

Same as Biblicus project.
