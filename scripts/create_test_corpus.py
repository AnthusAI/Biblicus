#!/usr/bin/env python3
"""
Create test corpus data in Amplify for local testing.

Usage:
    python scripts/create_test_corpus.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Load Amplify config
config_path = Path.home() / '.biblicus' / 'amplify.env'
if config_path.exists():
    with open(config_path) as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

from biblicus.sync.amplify_publisher import AmplifyPublisher

def main():
    print('Creating test corpus data...')

    publisher = AmplifyPublisher('test-corpus')

    # Create a test Corpus record
    mutation = '''
    mutation CreateCorpus($input: CreateCorpusInput!) {
      createCorpus(input: $input) {
        id
        name
        s3Prefix
        status
      }
    }
    '''

    variables = {
        'input': {
            'name': 'test-corpus',
            's3Prefix': 'test-corpus/',
            'status': 'IDLE',
            'createdAt': datetime.utcnow().isoformat() + 'Z',
            'updatedAt': datetime.utcnow().isoformat() + 'Z'
        }
    }

    try:
        result = publisher._execute_graphql(mutation, variables)
        print(f'✓ Created corpus: {result["createCorpus"]["name"]}')

        # Create a test Snapshot
        snapshot_mutation = '''
        mutation CreateSnapshot($input: CreateSnapshotInput!) {
          createSnapshot(input: $input) {
            corpusId
            snapshotId
            type
            status
          }
        }
        '''

        snapshot_vars = {
            'input': {
                'corpusId': 'test-corpus',
                'snapshotId': 'snapshot-001',
                'type': 'EXTRACTION',
                'status': 'COMPLETED',
                'totalItems': 100,
                'completedItems': 100,
                'startTime': datetime.utcnow().isoformat() + 'Z'
            }
        }

        result = publisher._execute_graphql(snapshot_mutation, snapshot_vars)
        print(f'✓ Created snapshot: {result["createSnapshot"]["snapshotId"]}')

        # Create some test CatalogItems
        for i in range(3):
            item_mutation = '''
            mutation CreateCatalogItem($input: CreateCatalogItemInput!) {
              createCatalogItem(input: $input) {
                corpusId
                itemId
                relpath
              }
            }
            '''

            item_vars = {
                'input': {
                    'corpusId': 'test-corpus',
                    'itemId': f'item-{i+1:03d}',
                    'relpath': f'documents/test-doc-{i+1}.txt',
                    'sha256': 'a' * 64,
                    'bytes': 1024 * (i + 1),
                    'mediaType': 'text/plain',
                    'title': f'Test Document {i+1}',
                    'createdAt': datetime.utcnow().isoformat() + 'Z',
                    'hasExtraction': i % 2 == 0
                }
            }

            result = publisher._execute_graphql(item_mutation, item_vars)
            print(f'✓ Created catalog item: {result["createCatalogItem"]["itemId"]}')

        print('\n✓ Test data created successfully!')
        print('Open http://localhost:5173 to view the dashboard')

        return 0
    except Exception as e:
        print(f'\n✗ Failed to create test data: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())
