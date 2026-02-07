#!/usr/bin/env python3
"""
Sync corpus catalog to AWS Amplify.

Usage:
    python scripts/sync_catalog.py ./corpora/wiki_demo
    python scripts/sync_catalog.py ./corpora/wiki_demo --force
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from biblicus.corpus import Corpus
from biblicus.sync.amplify_publisher import AmplifyPublisher


def main():
    parser = argparse.ArgumentParser(description="Sync catalog to Amplify")
    parser.add_argument('corpus_path', type=Path, help='Path to corpus')
    parser.add_argument('--force', action='store_true', help='Force full sync even if unchanged')

    args = parser.parse_args()

    # Load corpus
    corpus = Corpus.load(args.corpus_path)
    publisher = AmplifyPublisher(corpus.name)

    print(f'Syncing catalog for {corpus.name}...')

    try:
        result = publisher.sync_catalog(corpus.catalog_path, force=args.force)

        if result.skipped:
            print(f'✓ Catalog unchanged (hash: {result.hash[:8]}...)')
        else:
            print(f'✓ Synced: {result.created} created, {result.updated} updated, {result.deleted} deleted')

        if result.errors:
            print(f'⚠ {len(result.errors)} errors occurred:', file=sys.stderr)
            for error in result.errors[:5]:
                print(f'  - {error}', file=sys.stderr)
            if len(result.errors) > 5:
                print(f'  ... and {len(result.errors) - 5} more', file=sys.stderr)
            return 1

        return 0

    except Exception as e:
        print(f'✗ Sync failed: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
