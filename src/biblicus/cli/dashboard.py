"""
Dashboard synchronization commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..corpus import Corpus
from .common import (
    _add_common_corpus_arg,
)


def cmd_dashboard_sync(arguments: argparse.Namespace) -> int:
    """Sync corpus catalog to Amplify dashboard backend."""
    from ..sync.amplify_publisher import AmplifyPublisher

    corpus = (
        Corpus.open(arguments.corpus) if getattr(arguments, "corpus", None) else Corpus.discover()
    )

    # Create publisher
    publisher = AmplifyPublisher(corpus.name)

    print(f"Syncing {corpus.name} to dashboard backend...")

    # Create corpus record if it doesn't exist
    try:
        publisher.create_corpus()
        print("✓ Corpus record created/verified")
    except Exception as e:
        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
            print(f"✗ Failed to create corpus: {e}", file=sys.stderr)
            return 1

    # Sync catalog
    try:
        result = publisher.sync_catalog(corpus.catalog_path, force=arguments.force)

        if result.skipped:
            print(f"✓ Catalog unchanged (hash: {result.hash[:8]}...)")
        else:
            print(
                f"✓ Synced: {result.created} created, {result.updated} updated, {result.deleted} deleted"
            )

        if result.errors:
            print(f"⚠ {len(result.errors)} errors occurred:", file=sys.stderr)
            for error in result.errors[:5]:
                print(f"  - {error}", file=sys.stderr)
            if len(result.errors) > 5:
                print(f"  ... and {len(result.errors) - 5} more", file=sys.stderr)
            return 1

        return 0
    except Exception as e:
        print(f"✗ Sync failed: {e}", file=sys.stderr)
        return 1


def cmd_dashboard_configure(arguments: argparse.Namespace) -> int:
    """Configure Amplify backend credentials."""
    # Save configuration to ~/.biblicus/amplify.env
    config_dir = Path.home() / ".biblicus"
    config_dir.mkdir(exist_ok=True)

    config_path = config_dir / "amplify.env"

    config_content = f"""# Amplify Dashboard Backend Configuration
AMPLIFY_APPSYNC_ENDPOINT={arguments.endpoint}
AMPLIFY_API_KEY={arguments.api_key}
AMPLIFY_S3_BUCKET={arguments.bucket}
AWS_REGION={arguments.region}
"""

    config_path.write_text(config_content)
    print(f"✓ Configuration saved to {config_path}")
    print()
    print("Auto-sync will now work automatically after extraction/ingest.")
    print("Set AMPLIFY_AUTO_SYNC_CATALOG=false to disable auto-sync.")

    return 0


def register_dashboard_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the dashboard commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_dashboard = subparsers.add_parser(
        "dashboard", help="Manage dashboard backend synchronization."
    )
    dashboard_sub = p_dashboard.add_subparsers(dest="dashboard_command", required=True)

    p_dashboard_sync = dashboard_sub.add_parser("sync", help="Sync corpus to dashboard backend.")
    _add_common_corpus_arg(p_dashboard_sync)
    p_dashboard_sync.add_argument(
        "--force",
        action="store_true",
        help="Force full sync even if catalog unchanged.",
    )
    p_dashboard_sync.set_defaults(func=cmd_dashboard_sync)

    p_dashboard_configure = dashboard_sub.add_parser(
        "configure", help="Configure Amplify backend credentials."
    )
    p_dashboard_configure.add_argument(
        "--endpoint",
        required=True,
        help="AppSync GraphQL endpoint URL.",
    )
    p_dashboard_configure.add_argument(
        "--api-key",
        required=True,
        help="AppSync API key.",
    )
    p_dashboard_configure.add_argument(
        "--bucket",
        required=True,
        help="S3 bucket name for corpus storage.",
    )
    p_dashboard_configure.add_argument(
        "--region",
        default="us-west-2",
        help="AWS region (default: us-west-2).",
    )
    p_dashboard_configure.set_defaults(func=cmd_dashboard_configure)
