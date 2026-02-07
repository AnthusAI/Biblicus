# Biblicus Dashboard - Deployment Guide

## 🎉 Successfully Deployed!

The Biblicus Corpus Viewer dashboard is now live with a fully functional cloud backend.

### Production URLs
- **Dashboard**: https://main.d2tt8jli0p2lze.amplifyapp.com
- **Backend**: AWS Amplify Gen 2 (AppSync GraphQL + DynamoDB + S3)

## Quick Start

### 1. Configure Dashboard Backend (One-time setup)

```bash
# Get fresh production config
cd apps/dashboard
npx ampx generate outputs --branch main --app-id d2tt8jli0p2lze

# Extract and save credentials
biblicus dashboard configure \
  --endpoint $(jq -r '.data.url' amplify_outputs.json) \
  --api-key $(jq -r '.data.api_key' amplify_outputs.json) \
  --bucket $(jq -r '.storage.bucket_name' amplify_outputs.json) \
  --region $(jq -r '.data.aws_region' amplify_outputs.json)
```

### 2. Use Biblicus Normally (Auto-sync enabled!)

```bash
# Ingest, extract, analyze - everything syncs automatically!
biblicus ingest --text "Hello world"
biblicus extract
biblicus analyze

# Dashboard updates in real-time ✨
```

### 3. Manual Sync (Optional)

```bash
# Sync specific corpus
biblicus dashboard sync --corpus corpora/Alfa

# Force full re-sync
biblicus dashboard sync --corpus corpora/Alfa --force
```

## Architecture

### Backend (Amplify Gen 2)
- **AppSync GraphQL API** - Real-time data access
- **DynamoDB** - Corpus, CatalogItem, Snapshot, FileMetadata tables
- **S3** - Corpus file storage
- **Cognito** - User authentication
- **Lambda** - S3 event processing

### Frontend (Vite + React)
- **React 18** - UI framework
- **React Router** - Client-side routing  
- **Amplify Client** - Backend integration
- **GSAP** - Smooth animations
- **Tailwind CSS + Shadcn UI** - Styling

### Auto-Sync
- Enabled by default with `AMPLIFY_AUTO_SYNC_CATALOG=true`
- Triggers automatically after ingest/extract
- Idempotent - only syncs changed items
- Non-blocking - errors don't fail extraction

## Development

### Local with Production Backend

```bash
cd apps/dashboard
echo "VITE_USE_AMPLIFY=true" > .env.local
npm run dev
```

### Local with Mock Data

```bash
npm run dev:all  # Starts both local API and frontend
```

## Commands

```bash
biblicus dashboard configure   # Set up credentials
biblicus dashboard sync        # Manual sync
./scripts/sync_to_production.sh Alfa  # Quick sync
```

## Status

✅ Backend deployed
✅ Frontend live
✅ Auto-sync working
✅ Alfa corpus synced (594 items)
