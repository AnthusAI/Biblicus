"""
User configuration file loading for Biblicus.

User configuration is intended for small, local settings such as credentials for optional
integrations. It is separate from corpus configuration.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from ._vendor.dotyaml import ConfigLoader


class OpenAiUserConfig(BaseModel):
    """
    Configuration for OpenAI integrations.

    :ivar api_key: OpenAI API key used for authenticated requests.
    :vartype api_key: str
    """

    model_config = ConfigDict(extra="forbid")

    api_key: str = Field(min_length=1)


class HuggingFaceUserConfig(BaseModel):
    """
    Configuration for HuggingFace integrations.

    :ivar api_key: HuggingFace API key used for authenticated requests.
    :vartype api_key: str
    """

    model_config = ConfigDict(extra="forbid")

    api_key: str = Field(min_length=1)


class DeepgramUserConfig(BaseModel):
    """
    Configuration for Deepgram integrations.

    :ivar api_key: Deepgram API key used for authenticated requests.
    :vartype api_key: str
    """

    model_config = ConfigDict(extra="forbid")

    api_key: str = Field(min_length=1)


class BiblicusUserConfig(BaseModel):
    """
    Parsed user configuration for Biblicus.

    :ivar openai: Optional OpenAI configuration.
    :vartype openai: OpenAiUserConfig or None
    :ivar huggingface: Optional HuggingFace configuration.
    :vartype huggingface: HuggingFaceUserConfig or None
    :ivar deepgram: Optional Deepgram configuration.
    :vartype deepgram: DeepgramUserConfig or None
    """

    model_config = ConfigDict(extra="forbid")

    openai: Optional[OpenAiUserConfig] = None
    huggingface: Optional[HuggingFaceUserConfig] = None
    deepgram: Optional[DeepgramUserConfig] = None


def default_user_config_paths(
    *, cwd: Optional[Path] = None, home: Optional[Path] = None
) -> list[Path]:
    """
    Compute the default user configuration file search paths.

    The search order is:

    1. Home configuration: ``~/.biblicus/config.yml``
    2. Local configuration: ``./.biblicus/config.yml``

    Local configuration overrides home configuration when both exist.

    :param cwd: Optional working directory to use instead of the process current directory.
    :type cwd: Path or None
    :param home: Optional home directory to use instead of the current user's home directory.
    :type home: Path or None
    :return: Ordered list of configuration file paths.
    :rtype: list[Path]
    """
    resolved_home = (home or Path.home()).expanduser()
    resolved_cwd = cwd or Path.cwd()
    return [
        resolved_home / ".biblicus" / "config.yml",
        resolved_cwd / ".biblicus" / "config.yml",
    ]


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {key: value for key, value in base.items()}
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_dotyaml_data(path: Path) -> Dict[str, Any]:
    """
    Load a dotyaml configuration file and return a nested mapping.

    :param path: Configuration file path.
    :type path: Path
    :return: Parsed YAML data mapping.
    :rtype: dict[str, Any]
    """
    loader = ConfigLoader(prefix="", load_dotenv_first=False)
    loaded = loader.load_from_yaml(path)
    return loaded if isinstance(loaded, dict) else {}


def load_user_config(*, paths: Optional[list[Path]] = None) -> BiblicusUserConfig:
    """
    Load user configuration from known locations.

    This function merges multiple configuration files in order. Later files override earlier files.

    :param paths: Optional explicit search paths. When omitted, the default paths are used.
    :type paths: list[Path] or None
    :return: Parsed user configuration. When no files exist, the configuration is empty.
    :rtype: BiblicusUserConfig
    :raises ValueError: If an existing configuration file is not parseable.
    """
    search_paths = paths or default_user_config_paths()
    merged_data: Dict[str, Any] = {}

    for path in search_paths:
        if not path.is_file():
            continue
        loaded = _load_dotyaml_data(path)
        merged_data = _deep_merge(merged_data, loaded)

    return BiblicusUserConfig.model_validate(merged_data)


def resolve_openai_api_key(*, config: Optional[BiblicusUserConfig] = None) -> Optional[str]:
    """
    Resolve an OpenAI API key from environment or user configuration.

    Environment takes precedence over configuration.

    :param config: Optional pre-loaded user configuration.
    :type config: BiblicusUserConfig or None
    :return: API key string, or None when no key is available.
    :rtype: str or None
    """
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        return env_key
    loaded = config or load_user_config()
    if loaded.openai is None:
        return None
    return loaded.openai.api_key


def resolve_huggingface_api_key(
    *, config: Optional[BiblicusUserConfig] = None
) -> Optional[str]:
    """
    Resolve a HuggingFace API key from environment or user configuration.

    Environment takes precedence over configuration.

    :param config: Optional pre-loaded user configuration.
    :type config: BiblicusUserConfig or None
    :return: API key string, or None when no key is available.
    :rtype: str or None
    """
    env_key = os.environ.get("HUGGINGFACE_API_KEY")
    if env_key:
        return env_key
    loaded = config or load_user_config()
    if loaded.huggingface is None:
        return None
    return loaded.huggingface.api_key


def resolve_deepgram_api_key(
    *, config: Optional[BiblicusUserConfig] = None
) -> Optional[str]:
    """
    Resolve a Deepgram API key from environment or user configuration.

    Environment takes precedence over configuration.

    :param config: Optional pre-loaded user configuration.
    :type config: BiblicusUserConfig or None
    :return: API key string, or None when no key is available.
    :rtype: str or None
    """
    env_key = os.environ.get("DEEPGRAM_API_KEY")
    if env_key:
        return env_key
    loaded = config or load_user_config()
    if loaded.deepgram is None:
        return None
    return loaded.deepgram.api_key
