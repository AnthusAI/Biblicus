"""
Behavior-driven development and coverage test runner for Biblicus.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    """
    Resolve the repository root directory.

    :return: Repository root path.
    :rtype: Path
    """

    return Path(__file__).resolve().parent.parent


def _env_with_src() -> dict[str, str]:
    """
    Build an environment with src/ on PYTHONPATH.

    :return: Environment mapping.
    :rtype: dict[str, str]
    """

    repo_root = _repo_root()
    env = dict(os.environ)
    src = str(repo_root / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def _run(command: list[str], *, env: dict[str, str]) -> int:
    """
    Run a subprocess command with the provided environment.

    :param command: Command arguments.
    :type command: list[str]
    :param env: Environment mapping.
    :type env: dict[str, str]
    :return: Process exit code.
    :rtype: int
    """

    return subprocess.call(command, env=env)


def main() -> int:
    """
    Execute Behave under coverage and emit Hypertext Markup Language reports.

    By default, scenarios tagged ``@integration`` are excluded. Use ``--integration`` to
    include them.

    :return: Exit code.
    :rtype: int
    """

    parser = argparse.ArgumentParser(description="Run Biblicus behavior specs under coverage.")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Include scenarios tagged @integration.",
    )
    args = parser.parse_args()

    repo_root = _repo_root()
    env = _env_with_src()
    reports_dir = repo_root / "reports"
    htmlcov_dir = reports_dir / "htmlcov"

    _run([sys.executable, "-m", "coverage", "erase"], env=env)

    behave_args = [] if args.integration else ["--tags", "~@integration"]
    rc = _run([sys.executable, "-m", "coverage", "run", "-m", "behave", *behave_args], env=env)
    _run([sys.executable, "-m", "coverage", "report", "-m"], env=env)
    _run([sys.executable, "-m", "coverage", "html", "-d", str(htmlcov_dir)], env=env)

    print(f"Coverage report in Hypertext Markup Language: {htmlcov_dir / 'index.html'}")
    return int(rc)


if __name__ == "__main__":
    raise SystemExit(main())
