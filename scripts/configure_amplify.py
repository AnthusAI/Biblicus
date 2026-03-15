#!/usr/bin/env python3
"""
Configure AWS Amplify integration for Biblicus.

Usage:
    python scripts/configure_amplify.py \\
        --endpoint https://xxxxx.appsync-api.us-east-1.amazonaws.com/graphql \\
        --api-key da2-xxxxx \\
        --bucket biblicus-corpus-xxxxx \\
        --region us-east-1
"""

import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Configure AWS Amplify integration")
    parser.add_argument('--endpoint', required=True, help='AppSync GraphQL endpoint')
    parser.add_argument('--api-key', required=True, help='AppSync API key')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')

    args = parser.parse_args()

    config = {
        'AMPLIFY_APPSYNC_ENDPOINT': args.endpoint,
        'AMPLIFY_API_KEY': args.api_key,
        'AMPLIFY_S3_BUCKET': args.bucket,
        'AWS_REGION': args.region,
    }

    # Save to ~/.biblicus/amplify.env
    config_dir = Path.home() / '.biblicus'
    config_dir.mkdir(exist_ok=True)

    env_file = config_dir / 'amplify.env'
    with open(env_file, 'w') as f:
        for key, value in config.items():
            f.write(f'{key}={value}\n')

    print(f'✓ Amplify configuration saved to {env_file}')
    print('  Add this to your shell profile:')
    print(f'  export $(cat {env_file} | xargs)')


if __name__ == '__main__':
    main()
