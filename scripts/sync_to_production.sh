#!/bin/bash
# Sync corpus to production Amplify backend
# Usage: ./scripts/sync_to_production.sh corpus-name [path-to-corpus]

set -e

CORPUS_NAME="${1}"
CORPUS_PATH="${2:-corpora/${CORPUS_NAME}}"

if [ -z "$CORPUS_NAME" ]; then
    echo "Usage: $0 <corpus-name> [path-to-corpus]"
    echo "Example: $0 Alfa"
    echo "Example: $0 Demo corpora/Demo"
    exit 1
fi

if [ ! -d "$CORPUS_PATH" ]; then
    echo "Error: Corpus path not found: $CORPUS_PATH"
    exit 1
fi

# Get production backend config from amplify_outputs.json
OUTPUTS_FILE="apps/dashboard/amplify_outputs.json"

if [ ! -f "$OUTPUTS_FILE" ]; then
    echo "Error: amplify_outputs.json not found. Run: npx ampx generate outputs --branch main --app-id d2tt8jli0p2lze"
    exit 1
fi

export AMPLIFY_APPSYNC_ENDPOINT=$(jq -r '.data.url' "$OUTPUTS_FILE")
export AMPLIFY_API_KEY=$(jq -r '.data.api_key' "$OUTPUTS_FILE")
export AMPLIFY_S3_BUCKET=$(jq -r '.storage.bucket_name' "$OUTPUTS_FILE")
export AWS_REGION=$(jq -r '.data.aws_region' "$OUTPUTS_FILE")

echo "=== Syncing $CORPUS_NAME to production ==="
echo "Endpoint: $AMPLIFY_APPSYNC_ENDPOINT"
echo "Bucket: $AMPLIFY_S3_BUCKET"
echo ""

# Create corpus record
echo "Creating corpus record..."
python3 -c "
from biblicus.sync.amplify_publisher import AmplifyPublisher
publisher = AmplifyPublisher('$CORPUS_NAME')
try:
    result = publisher.create_corpus()
    print(f'✓ Created corpus: {result}')
except Exception as e:
    if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
        print('✓ Corpus already exists')
    else:
        raise
"

# Sync catalog
echo ""
echo "Syncing catalog..."
python scripts/sync_catalog.py "$CORPUS_PATH"

echo ""
echo "✓ Sync complete!"
echo "View at: http://localhost:5175 (local) or https://main.d2tt8jli0p2lze.amplifyapp.com (production)"
