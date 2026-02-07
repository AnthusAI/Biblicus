# Deployment Guide

## Initial Amplify Setup

### 1. Install Amplify CLI

```bash
npm install -g @aws-amplify/cli
```

### 2. Configure AWS Credentials

Make sure you have AWS credentials configured:

```bash
aws configure
```

### 3. Initialize Amplify App

From the Amplify Console (https://console.aws.amazon.com/amplify/):

1. Click "Create new app"
2. Choose "Deploy without Git provider"
3. Name your app (e.g., "biblicus-dashboard")
4. Note the App ID (you'll need this)

### 4. Deploy Backend

```bash
cd apps/dashboard
npm install

# Deploy to production
npx ampx pipeline-deploy --branch main --app-id YOUR_AMPLIFY_APP_ID
```

This will deploy:
- AppSync GraphQL API with DynamoDB tables
- S3 bucket for corpus storage
- Cognito user pool for authentication
- Lambda function for S3 event handling

### 5. Get Connection Details

After deployment completes, run:

```bash
npx ampx generate outputs --branch main --app-id YOUR_AMPLIFY_APP_ID
```

This generates `amplify_outputs.json` with all connection details.

Alternatively, get values from the Amplify Console:
- **AppSync Endpoint**: API section → GraphQL endpoint
- **API Key**: API section → API keys
- **S3 Bucket**: Storage section → Bucket name
- **User Pool ID**: Auth section → User pool ID

### 6. Configure Python CLI

Use the connection details to configure the Python CLI:

```bash
# From Biblicus project root
python scripts/configure_amplify.py \
  --endpoint YOUR_APPSYNC_ENDPOINT \
  --api-key YOUR_API_KEY \
  --bucket YOUR_S3_BUCKET_NAME \
  --region us-east-1
```

This creates `~/.biblicus/amplify.env` with:
```
AMPLIFY_APPSYNC_ENDPOINT=https://xxx.appsync-api.us-east-1.amazonaws.com/graphql
AMPLIFY_API_KEY=da2-xxxxxxxxxxxxxxxxxxxxx
AMPLIFY_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1
```

### 7. Create First User

Create a Cognito user for frontend access:

```bash
aws cognito-idp sign-up \
  --region us-east-1 \
  --client-id YOUR_USER_POOL_CLIENT_ID \
  --username admin@example.com \
  --password YourSecurePassword123!
```

Then confirm the user:

```bash
aws cognito-idp admin-confirm-sign-up \
  --region us-east-1 \
  --user-pool-id YOUR_USER_POOL_ID \
  --username admin@example.com
```

## Development Workflow

### Run Frontend Locally

```bash
cd apps/dashboard
npm run dev
```

Open http://localhost:5173

### Test Backend Changes

After modifying files in `amplify/`:

```bash
npx ampx pipeline-deploy --branch main --app-id YOUR_AMPLIFY_APP_ID
```

### Test Python Integration

```bash
# Sync catalog manually
python scripts/sync_catalog.py ./corpora/your_corpus

# Run extraction with auto-sync
export AMPLIFY_AUTO_SYNC_CATALOG=true
# Run your extraction command
```

## Production Deployment

### Deploy Frontend

Build the frontend:

```bash
cd apps/dashboard
npm run build
```

Deploy the `dist/` folder to:
- **Amplify Hosting**: Connect your Git repo and configure build settings
- **S3 + CloudFront**: Upload to S3 bucket with CloudFront distribution
- **Vercel/Netlify**: Connect repo and configure as Vite app

### Environment Variables for Production

Frontend needs `amplify_outputs.json` in production. Options:

1. **Include in build**: Already done, file is read at build time
2. **Generate from env vars**: Use build script to generate from environment
3. **CDN/edge config**: Inject config at the edge (CloudFlare Workers, etc.)

## Troubleshooting

### "Module not found" errors

```bash
cd apps/dashboard
rm -rf node_modules package-lock.json
npm install
```

### GraphQL schema changes not reflected

```bash
# Redeploy backend
npx ampx pipeline-deploy --branch main --app-id YOUR_AMPLIFY_APP_ID

# Regenerate outputs
npx ampx generate outputs --branch main --app-id YOUR_AMPLIFY_APP_ID
```

### Python CLI can't connect

Check configuration:
```bash
cat ~/.biblicus/amplify.env
```

Test AWS credentials:
```bash
aws sts get-caller-identity
```

Verify S3 bucket access:
```bash
aws s3 ls s3://YOUR_BUCKET_NAME/
```

### CORS errors in browser

Update AppSync configuration to allow your frontend domain. In `amplify/data/resource.ts`, you may need to configure CORS settings.

## Cost Management

Monitor costs in AWS Cost Explorer:
- AppSync: Pay per request (~$4 per million requests)
- DynamoDB: Pay per read/write (~$1.25 per million reads)
- S3: Pay per GB stored (~$0.023 per GB)
- Lambda: Pay per invocation (free tier: 1M requests/month)

Typical cost for small corpus (1000 items, 10GB, 100K requests/month): **~$5/month**

## Rollback

If deployment fails or you need to rollback:

```bash
# Delete the Amplify app (WARNING: destroys all data)
aws amplify delete-app --app-id YOUR_AMPLIFY_APP_ID --region us-east-1
```

To preserve data, export from DynamoDB first:

```bash
# Export tables before deletion
aws dynamodb export-table-to-point-in-time \
  --table-arn arn:aws:dynamodb:REGION:ACCOUNT:table/TABLE_NAME \
  --s3-bucket YOUR_BACKUP_BUCKET \
  --export-format DYNAMODB_JSON
```
