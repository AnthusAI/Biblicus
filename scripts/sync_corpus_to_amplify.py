#!/usr/bin/env python3
"""
Sync an existing corpus to Amplify.

Usage:
    python scripts/sync_corpus_to_amplify.py corpora/markov-demo
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
from biblicus.corpus import Corpus

def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/sync_corpus_to_amplify.py <corpus-path>')
        return 1

    corpus_path = Path(sys.argv[1])
    if not corpus_path.exists():
        print(f'Error: Corpus path not found: {corpus_path}')
        return 1

    print(f'Syncing corpus: {corpus_path}')

    # Load the corpus
    corpus = Corpus(corpus_path)
    corpus_name = corpus_path.name

    print(f'Corpus name: {corpus_name}')

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
        print(f'✓ Created corpus record: {corpus_name}')
    except Exception as e:
        if 'already exists' in str(e) or 'DuplicateKey' in str(e):
            print(f'✓ Corpus record already exists: {corpus_name}')
        else:
            raise

    # Sync catalog if it exists
    catalog_path = corpus.root / 'catalog.json'
    if catalog_path.exists():
        print(f'Syncing catalog from {catalog_path}...')
        result = publisher.sync_catalog(catalog_path, force=True)
        print(f'✓ Synced catalog: {result.created} created, {result.updated} updated')
    else:
        print('No catalog.json found, skipping catalog sync')

    print(f'\n✓ Corpus synced successfully!')
    print(f'View at http://localhost:5173')

    return 0

if __name__ == '__main__':
    sys.exit(main())
