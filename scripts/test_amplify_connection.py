#!/usr/bin/env python3
"""
Test Amplify connection by creating a test corpus record.

Usage:
    python scripts/test_amplify_connection.py
"""

import os
import sys
from pathlib import Path

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
    print('Testing Amplify connection...')

    # Create publisher
    publisher = AmplifyPublisher('test-corpus')

    # Test GraphQL connection
    query = '''
    query ListCorpuses {
      listCorpuses {
        items {
          id
          name
          s3Prefix
        }
      }
    }
    '''

    try:
        result = publisher._execute_graphql(query, {})
        print(f'\n✓ Connection successful!')
        print(f'Found {len(result.get("listCorpuses", {}).get("items", []))} corpora')

        # Show existing corpora
        items = result.get("listCorpuses", {}).get("items", [])
        if items:
            print('\nExisting corpora:')
            for item in items:
                print(f'  - {item["name"]} (ID: {item["id"]})')
        else:
            print('\nNo corpora found yet.')
            print('\nTo create a test corpus, run a Biblicus extraction with AMPLIFY_AUTO_SYNC_CATALOG=true')

        return 0
    except Exception as e:
        print(f'\n✗ Connection failed: {e}')
        print('\nMake sure:')
        print('  1. The Amplify sandbox is running (npx ampx sandbox)')
        print('  2. The configuration is correct (~/.biblicus/amplify.env)')
        print('  3. AWS credentials are configured')
        return 1

if __name__ == '__main__':
    sys.exit(main())
