"""
Run unit tests, baseline behavior specs, and integration scenarios.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

import yaml


def _repo_root() -> Path:
    """
    Resolve the repository root directory.

    :return: Repository root path.
    :rtype: Path
    """
    return Path(__file__).resolve().parent.parent


def _load_openai_api_key(repo_root: Path) -> str:
    """
    Load the OpenAI API key from the local Biblicus configuration file.

    :param repo_root: Repository root path.
    :type repo_root: Path
    :return: OpenAI API key.
    :rtype: str
    :raises ValueError: If the API key is missing.
    """
    config_path = repo_root / ".biblicus" / "config.yml"
    if not config_path.exists():
        raise ValueError(
            "Missing .biblicus/config.yml. Set OPENAI_API_KEY or create the local config file."
        )
    config = yaml.safe_load(config_path.read_text()) or {}
    openai_config = config.get("openai") or {}
    api_key = openai_config.get("api_key")
    if not api_key:
        raise ValueError(
            "OpenAI API key is missing. Set OPENAI_API_KEY or add openai.api_key in .biblicus/config.yml."
        )
    return str(api_key)


def _run(command: list[str], *, env: Dict[str, str]) -> int:
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


def _env_without_key() -> Dict[str, str]:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    return env


def _env_with_key(api_key: str) -> Dict[str, str]:
    env = dict(os.environ)
    env["OPENAI_API_KEY"] = api_key
    env["BIBLICUS_RUN_MARKOV_DEMO"] = "1"
    env.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    return env


def _run_pytest(env: Dict[str, str]) -> int:
    return _run([sys.executable, "-m", "pytest"], env=env)


def _run_baseline_behave(env: Dict[str, str]) -> int:
    return _run([sys.executable, "-m", "behave", "--tags", "~@integration"], env=env)


def _run_integration_behave(*, repo_root: Path, env: Dict[str, str]) -> int:
    feature_paths = sorted((repo_root / "features").glob("integration_*.feature"))
    if not feature_paths:
        raise ValueError("No integration feature files found in features/.")
    return _run(
        [sys.executable, "-m", "behave", *[str(path) for path in feature_paths]],
        env=env,
    )


def main() -> int:
    """
    Run all unit, baseline, and integration tests.

    :return: Exit code.
    :rtype: int
    """
    repo_root = _repo_root()
    baseline_env = _env_without_key()
    pytest_code = _run_pytest(baseline_env)
    if pytest_code != 0:
        return pytest_code

    behave_code = _run_baseline_behave(baseline_env)
    if behave_code != 0:
        return behave_code

    api_key: Optional[str] = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = _load_openai_api_key(repo_root)
    integration_env = _env_with_key(api_key)
    return _run_integration_behave(repo_root=repo_root, env=integration_env)


if __name__ == "__main__":
    raise SystemExit(main())
