#!/usr/bin/env python3
"""
Discover and sync all corpora from the corpora/ folder to Amplify.

Usage:
    python scripts/sync_all_corpora.py
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

def discover_corpora(root_path: Path):
    """Discover all corpus directories in the corpora folder."""
    corpora = []

    # Look for directories in corpora/ that have a .biblicus subdirectory
    if not root_path.exists():
        print(f'Error: {root_path} does not exist')
        return corpora

    for item in root_path.iterdir():
        if item.is_dir() and (item / '.biblicus').exists():
            corpora.append(item)

    return corpora

def sync_corpus(corpus_path: Path):
    """Sync a single corpus to Amplify."""
    corpus_name = corpus_path.name

    print(f'\nSyncing corpus: {corpus_name}')

    # Create publisher
    publisher = AmplifyPublisher(corpus_name)

    # Create or update Corpus record
    mutation = '''
    mutation CreateCorpus($input: CreateCorpusInput!) {
      createCorpus(input: $input) {
        id
        name
        s3Prefix
        status
        createdAt
      }
    }
    '''

    variables = {
        'input': {
            'name': corpus_name,
            's3Prefix': f'{corpus_name}/',
            'status': 'IDLE',
            'createdAt': datetime.now().isoformat() + 'Z',
            'updatedAt': datetime.now().isoformat() + 'Z'
        }
    }

    try:
        result = publisher._execute_graphql(mutation, variables)
        print(f'  ✓ Created corpus record: {corpus_name}')
    except Exception as e:
        if 'already exists' in str(e) or 'DuplicateKey' in str(e):
            print(f'  ✓ Corpus record already exists: {corpus_name}')
        else:
            print(f'  ✗ Failed to create corpus record: {e}')
            return False

    # Sync catalog if it exists
    catalog_path = corpus_path / 'catalog.json'
    if catalog_path.exists():
        try:
            result = publisher.sync_catalog(catalog_path, force=False)
            if result.skipped:
                print(f'  ✓ Catalog unchanged')
            else:
                print(f'  ✓ Synced catalog: {result.created} created, {result.updated} updated')
        except Exception as e:
            print(f'  ✗ Catalog sync failed: {e}')
    else:
        print(f'  - No catalog.json found')

    return True

def main():
    # Find corpora directory
    corpora_root = Path(__file__).parent.parent / 'corpora'

    print(f'Discovering corpora in {corpora_root}...\n')

    corpora = discover_corpora(corpora_root)

    if not corpora:
        print('No corpora found!')
        return 1

    print(f'Found {len(corpora)} corpora:')
    for corpus in corpora:
        print(f'  - {corpus.name}')

    print('\nSyncing to Amplify...')

    synced = 0
    failed = 0

    for corpus_path in corpora:
        if sync_corpus(corpus_path):
            synced += 1
        else:
            failed += 1

    print(f'\n{"="*50}')
    print(f'✓ Synced {synced} corpora')
    if failed > 0:
        print(f'✗ Failed to sync {failed} corpora')
    print(f'\nView at http://localhost:5173')

    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
