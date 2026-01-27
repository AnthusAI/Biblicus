"""
Behavior-driven development and coverage test runner for Biblicus.
"""

from __future__ import annotations

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

    :return: Exit code.
    :rtype: int
    """

    repo_root = _repo_root()
    env = _env_with_src()
    reports_dir = repo_root / "reports"
    htmlcov_dir = reports_dir / "htmlcov"

    _run([sys.executable, "-m", "coverage", "erase"], env=env)

    rc = _run([sys.executable, "-m", "coverage", "run", "-m", "behave"], env=env)
    _run([sys.executable, "-m", "coverage", "report", "-m"], env=env)
    _run([sys.executable, "-m", "coverage", "html", "-d", str(htmlcov_dir)], env=env)

    print(f"Coverage report in Hypertext Markup Language: {htmlcov_dir / 'index.html'}")
    return int(rc)


if __name__ == "__main__":
    raise SystemExit(main())
