"""
Regenerate or verify the published JSON Schemas for the typed Biblicus application programming interface.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from biblicus.api.schemas import find_stale_api_schemas, write_api_schemas  # noqa: E402

DEFAULT_DIRECTORY = REPOSITORY_ROOT / "docs" / "api-schemas"


def main() -> int:
    """
    Write the schemas, or with ``--check`` fail when the published files are stale.

    :return: Zero when the schemas are written or current, one when ``--check`` finds drift.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the published schemas match the models instead of writing them.",
    )
    arguments = parser.parse_args()
    if arguments.check:
        problems = find_stale_api_schemas(arguments.directory)
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if problems else 0
    for file_name in write_api_schemas(arguments.directory):
        print(file_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
