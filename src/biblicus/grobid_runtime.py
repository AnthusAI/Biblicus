"""
Just-in-time GROBID runtime management (Docker auto-start for localhost).
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import List
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_GROBID_URL = "http://127.0.0.1:8070"
DEFAULT_GROBID_DOCKER_IMAGE = "lfoppiano/grobid:0.8.0"
DEFAULT_GROBID_CONTAINER_NAME = "papyrus-grobid"
URL_TEXT_GROBID_URL_ENV = "BIBLICUS_GROBID_URL"
GROBID_AUTO_START_ENV = "BIBLICUS_GROBID_AUTO_START"
GROBID_CONTAINER_NAME_ENV = "BIBLICUS_GROBID_CONTAINER_NAME"
GROBID_DOCKER_IMAGE_ENV = "BIBLICUS_GROBID_DOCKER_IMAGE"
PAPYRUS_GROBID_CONTAINER_NAME_ENV = "PAPYRUS_GROBID_CONTAINER_NAME"
PAPYRUS_GROBID_DOCKER_IMAGE_ENV = "PAPYRUS_GROBID_DOCKER_IMAGE"

DOCKER_CANDIDATE_PATHS = (
    "/usr/local/bin/docker",
    "/opt/homebrew/bin/docker",
    "/Applications/Docker.app/Contents/Resources/bin/docker",
)

_ENSURE_LOCK = __import__("threading").Lock()
_ENSURED_URL: str | None = None


def grobid_auto_start_enabled() -> bool:
    """
    Return whether localhost GROBID should be auto-started via Docker.

    :return: True when auto-start is enabled.
    :rtype: bool
    """
    raw = os.environ.get(GROBID_AUTO_START_ENV)
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return True


def resolve_grobid_base_url() -> str:
    """
    Resolve the GROBID base URL from environment or defaults.

    :return: Base URL without trailing slash.
    :rtype: str
    """
    explicit = (
        str(os.environ.get(URL_TEXT_GROBID_URL_ENV) or "").strip()
        or str(os.environ.get("PAPYRUS_GROBID_URL") or "").strip()
    )
    if explicit:
        return explicit.rstrip("/")
    return DEFAULT_GROBID_URL


def ensure_grobid_running(grobid_url: str | None = None) -> str:
    """
    Ensure GROBID is reachable, auto-starting a local Docker container when configured.

    :param grobid_url: Optional explicit base URL; defaults to :func:`resolve_grobid_base_url`.
    :type grobid_url: str or None
    :return: Verified GROBID base URL.
    :rtype: str
    :raises RuntimeError: When GROBID cannot be started or reached.
    """
    global _ENSURED_URL
    base_url = (grobid_url or resolve_grobid_base_url()).rstrip("/")
    with _ENSURE_LOCK:
        if _ENSURED_URL == base_url and grobid_is_alive(base_url):
            return base_url
        if _ENSURED_URL is not None and not grobid_is_alive(_ENSURED_URL):
            _ENSURED_URL = None
        if grobid_is_alive(base_url):
            _ENSURED_URL = base_url
            return base_url
        if not grobid_auto_start_enabled():
            raise RuntimeError(
                f"GROBID is not reachable at {base_url} and {GROBID_AUTO_START_ENV} is disabled."
            )
        parsed = urlparse(base_url)
        host = (parsed.hostname or "").strip().lower()
        port = int(parsed.port or (443 if parsed.scheme == "https" else 80))
        if host not in {"127.0.0.1", "localhost"}:
            raise RuntimeError(
                f"GROBID is not reachable at {base_url}. Auto-start is only supported for localhost endpoints."
            )
        _start_or_reuse_local_grobid_container(port=port)
        _await_grobid_ready(base_url)
        _ENSURED_URL = base_url
        return base_url


def grobid_is_alive(grobid_url: str) -> bool:
    """
    Probe GROBID ``/api/isalive``.

    :param grobid_url: GROBID base URL.
    :type grobid_url: str
    :return: True when the service responds successfully.
    :rtype: bool
    """
    probe_url = f"{grobid_url.rstrip('/')}/api/isalive"
    request = Request(probe_url, method="GET")
    try:
        with urlopen(request, timeout=2.0) as response:
            status = int(getattr(response, "status", response.getcode()))
            if status < 200 or status >= 300:
                return False
            payload = response.read().decode("utf-8", errors="replace").strip().lower()
            return "true" in payload or payload == ""
    except Exception:
        return False


def _grobid_container_name() -> str:
    return (
        str(os.environ.get(GROBID_CONTAINER_NAME_ENV) or "").strip()
        or str(os.environ.get(PAPYRUS_GROBID_CONTAINER_NAME_ENV) or "").strip()
        or DEFAULT_GROBID_CONTAINER_NAME
    )


def _grobid_docker_image() -> str:
    return (
        str(os.environ.get(GROBID_DOCKER_IMAGE_ENV) or "").strip()
        or str(os.environ.get(PAPYRUS_GROBID_DOCKER_IMAGE_ENV) or "").strip()
        or DEFAULT_GROBID_DOCKER_IMAGE
    )


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex((host, port)) == 0


def _start_or_reuse_local_grobid_container(*, port: int) -> None:
    docker_command = _resolve_docker_command()
    if not docker_command:
        raise RuntimeError(
            "Docker binary was not found. Cannot auto-start local GROBID container. "
            "Install Docker Desktop/CLI or point BIBLICUS_GROBID_URL at a reachable service."
        )
    _ensure_docker_daemon_ready(docker_command)

    container_name = _grobid_container_name()
    image = _grobid_docker_image()
    running = _docker_lines(
        docker_command,
        [
            "ps",
            "--filter",
            f"name=^/{container_name}$",
            "--filter",
            "status=running",
            "--format",
            "{{.ID}}",
        ],
    )
    if running:
        return

    existing = _docker_lines(
        docker_command,
        [
            "ps",
            "-a",
            "--filter",
            f"name=^/{container_name}$",
            "--format",
            "{{.ID}}",
        ],
    )
    if existing:
        completed = subprocess.run(
            [docker_command, "start", container_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"Failed to start existing GROBID container {container_name}: {stderr}")
        return

    completed = subprocess.run(
        [
            docker_command,
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{port}:8070",
            image,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"Failed to launch GROBID container {container_name} using {image}: {stderr}")


def _await_grobid_ready(grobid_url: str) -> None:
    deadline = time.time() + 120.0
    parsed = urlparse(grobid_url)
    host = (parsed.hostname or "127.0.0.1").strip()
    port = int(parsed.port or (443 if parsed.scheme == "https" else 80))
    while time.time() < deadline:
        if _port_is_open(host, port) and grobid_is_alive(grobid_url):
            return
        time.sleep(1.5)
    raise RuntimeError(
        f"GROBID did not become ready at {grobid_url} after container start. "
        "Check Docker container logs and retry."
    )


def _resolve_docker_command() -> str | None:
    command = shutil.which("docker")
    if command:
        return command
    for candidate in DOCKER_CANDIDATE_PATHS:
        if Path(candidate).is_file():
            return candidate
    return None


def _docker_daemon_ready(docker_command: str) -> bool:
    completed = subprocess.run(
        [docker_command, "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _ensure_docker_daemon_ready(docker_command: str) -> None:
    if _docker_daemon_ready(docker_command):
        return
    if sys.platform == "darwin" and Path("/Applications/Docker.app").exists():
        subprocess.run(
            ["open", "-a", "Docker"],
            capture_output=True,
            text=True,
            check=False,
        )
        deadline = time.time() + 90.0
        while time.time() < deadline:
            if _docker_daemon_ready(docker_command):
                return
            time.sleep(1.5)
    raise RuntimeError(
        "Docker daemon is not ready for GROBID auto-start. "
        "Start Docker Desktop and retry, or point BIBLICUS_GROBID_URL at a reachable service."
    )


def _docker_lines(docker_command: str, command: List[str]) -> List[str]:
    completed = subprocess.run(
        [docker_command, *command],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
