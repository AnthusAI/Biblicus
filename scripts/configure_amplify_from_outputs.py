#!/usr/bin/env python3
"""
Configure Amplify integration from amplify_outputs.json.

Usage:
    python scripts/configure_amplify_from_outputs.py
"""

import json
import os
from pathlib import Path

def main():
    # Load amplify_outputs.json
    outputs_path = Path(__file__).parent.parent / 'apps' / 'dashboard' / 'amplify_outputs.json'

    if not outputs_path.exists():
        print(f'Error: {outputs_path} not found')
        print('Run "npx ampx sandbox" in apps/dashboard first')
        return 1

    with open(outputs_path) as f:
        outputs = json.load(f)

    # Extract values
    endpoint = outputs['data']['url']
    api_key = outputs['data']['api_key']
    bucket = outputs['storage']['bucket_name']
    region = outputs['data']['aws_region']

    # Create config directory
    config_dir = Path.home() / '.biblicus'
    config_dir.mkdir(exist_ok=True)

    # Write config
    config_path = config_dir / 'amplify.env'
    with open(config_path, 'w') as f:
        f.write(f'AMPLIFY_APPSYNC_ENDPOINT={endpoint}\n')
        f.write(f'AMPLIFY_API_KEY={api_key}\n')
        f.write(f'AMPLIFY_S3_BUCKET={bucket}\n')
        f.write(f'AWS_REGION={region}\n')

    print(f'✓ Configuration saved to {config_path}')
    print(f'\nEndpoint: {endpoint}')
    print(f'API Key: {api_key[:10]}...')
    print(f'Bucket: {bucket}')
    print(f'Region: {region}')
    print(f'\nTo enable auto-sync after extraction, run:')
    print(f'  export AMPLIFY_AUTO_SYNC_CATALOG=true')

    return 0

if __name__ == '__main__':
    exit(main())
