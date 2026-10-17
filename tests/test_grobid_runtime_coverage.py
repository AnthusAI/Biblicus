"""Coverage tests for GROBID runtime management and GROBID request helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from biblicus import grobid_client, grobid_runtime
from biblicus.url_text import UrlTextExtractionError


class _FakeIsAliveResponse:
    def __init__(self, *, status_code, payload_bytes, expose_status_attribute=True):
        if expose_status_attribute:
            self.status = status_code
        self._status_code = status_code
        self._payload_bytes = payload_bytes

    def getcode(self):
        return self._status_code

    def read(self):
        return self._payload_bytes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class _FakeClock:
    def __init__(self, *, step_seconds):
        self.current_seconds = 0.0
        self.step_seconds = step_seconds
        self.slept_durations = []

    def time(self):
        self.current_seconds += self.step_seconds
        return self.current_seconds

    def sleep(self, seconds):
        self.slept_durations.append(seconds)


class _RecordingSubprocess:
    def __init__(self, completed_results):
        self.completed_results = list(completed_results)
        self.recorded_commands = []

    def run(self, command, **_kwargs):
        self.recorded_commands.append(list(command))
        return self.completed_results.pop(0)


def _completed_process(*, returncode, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def reset_ensured_grobid_url(monkeypatch):
    """Reset the cached ensured GROBID URL for the duration of a test."""
    monkeypatch.setattr(grobid_runtime, "_ENSURED_URL", None)


@pytest.mark.parametrize(
    ("raw_value", "expected_enabled"),
    [(" YES ", True), ("on", True), ("0", False), ("false", False)],
)
def test_grobid_auto_start_enabled_reads_environment_flag(monkeypatch, raw_value, expected_enabled):
    """Verify that grobid auto start enabled reads environment flag."""
    monkeypatch.setenv("BIBLICUS_GROBID_AUTO_START", raw_value)
    assert grobid_runtime.grobid_auto_start_enabled() is expected_enabled


def test_grobid_auto_start_enabled_defaults_to_true(monkeypatch):
    """Verify that grobid auto start enabled defaults to true."""
    monkeypatch.delenv("BIBLICUS_GROBID_AUTO_START", raising=False)
    assert grobid_runtime.grobid_auto_start_enabled() is True


def test_resolve_grobid_base_url_prefers_biblicus_environment_and_strips_slash(monkeypatch):
    """Verify that resolve grobid base url prefers biblicus environment and strips slash."""
    monkeypatch.setenv("BIBLICUS_GROBID_URL", " http://grobid.example:9000/ ")
    monkeypatch.setenv("PAPYRUS_GROBID_URL", "http://papyrus.example:9000")
    assert grobid_runtime.resolve_grobid_base_url() == "http://grobid.example:9000"


def test_resolve_grobid_base_url_uses_papyrus_environment_when_biblicus_missing(monkeypatch):
    """Verify that resolve grobid base url uses papyrus environment when biblicus missing."""
    monkeypatch.delenv("BIBLICUS_GROBID_URL", raising=False)
    monkeypatch.setenv("PAPYRUS_GROBID_URL", "http://papyrus.example:9000/")
    assert grobid_runtime.resolve_grobid_base_url() == "http://papyrus.example:9000"


def test_ensure_grobid_running_returns_cached_url_when_still_alive(
    monkeypatch, reset_ensured_grobid_url
):
    """Verify that ensure grobid running returns cached url when still alive."""
    probed_urls = []

    def record_alive_probe(url):
        probed_urls.append(url)
        return True

    monkeypatch.setattr(grobid_runtime, "_ENSURED_URL", "http://127.0.0.1:8070")
    monkeypatch.setattr(grobid_runtime, "grobid_is_alive", record_alive_probe)
    assert grobid_runtime.ensure_grobid_running("http://127.0.0.1:8070/") == "http://127.0.0.1:8070"
    assert probed_urls == ["http://127.0.0.1:8070"]


def test_ensure_grobid_running_forgets_stale_cached_url_and_rejects_when_auto_start_disabled(
    monkeypatch, reset_ensured_grobid_url
):
    """Verify that ensure grobid running forgets stale cached url and rejects when auto start disabled."""
    monkeypatch.setattr(grobid_runtime, "_ENSURED_URL", "http://127.0.0.1:9999")
    monkeypatch.setattr(grobid_runtime, "grobid_is_alive", lambda _url: False)
    monkeypatch.setenv("BIBLICUS_GROBID_AUTO_START", "off")
    with pytest.raises(RuntimeError, match="BIBLICUS_GROBID_AUTO_START is disabled"):
        grobid_runtime.ensure_grobid_running("http://127.0.0.1:8070")
    assert grobid_runtime._ENSURED_URL is None


def test_ensure_grobid_running_keeps_live_cached_url_and_adopts_new_live_url(
    monkeypatch, reset_ensured_grobid_url
):
    """Verify that ensure grobid running keeps live cached url and adopts new live url."""
    monkeypatch.setattr(grobid_runtime, "_ENSURED_URL", "http://127.0.0.1:9999")
    monkeypatch.setattr(grobid_runtime, "grobid_is_alive", lambda _url: True)
    assert grobid_runtime.ensure_grobid_running("http://127.0.0.1:8070") == "http://127.0.0.1:8070"
    assert grobid_runtime._ENSURED_URL == "http://127.0.0.1:8070"


def test_ensure_grobid_running_uses_resolved_default_url(monkeypatch, reset_ensured_grobid_url):
    """Verify that ensure grobid running uses resolved default url."""
    monkeypatch.delenv("BIBLICUS_GROBID_URL", raising=False)
    monkeypatch.delenv("PAPYRUS_GROBID_URL", raising=False)
    monkeypatch.setattr(grobid_runtime, "grobid_is_alive", lambda _url: True)
    assert grobid_runtime.ensure_grobid_running() == "http://127.0.0.1:8070"


def test_ensure_grobid_running_rejects_remote_https_endpoint_without_port(
    monkeypatch, reset_ensured_grobid_url
):
    """Verify that ensure grobid running rejects remote https endpoint without port."""
    monkeypatch.delenv("BIBLICUS_GROBID_AUTO_START", raising=False)
    monkeypatch.setattr(grobid_runtime, "grobid_is_alive", lambda _url: False)
    with pytest.raises(RuntimeError, match="only supported for localhost"):
        grobid_runtime.ensure_grobid_running("https://grobid.example")


def test_ensure_grobid_running_starts_localhost_container_on_default_http_port(
    monkeypatch, reset_ensured_grobid_url
):
    """Verify that ensure grobid running starts localhost container on default http port."""
    started_ports = []
    awaited_urls = []
    monkeypatch.delenv("BIBLICUS_GROBID_AUTO_START", raising=False)
    monkeypatch.setattr(grobid_runtime, "grobid_is_alive", lambda _url: False)
    monkeypatch.setattr(
        grobid_runtime,
        "_start_or_reuse_local_grobid_container",
        lambda *, port: started_ports.append(port),
    )
    monkeypatch.setattr(grobid_runtime, "_await_grobid_ready", awaited_urls.append)
    assert grobid_runtime.ensure_grobid_running("http://localhost") == "http://localhost"
    assert started_ports == [80]
    assert awaited_urls == ["http://localhost"]
    assert grobid_runtime._ENSURED_URL == "http://localhost"


@pytest.mark.parametrize(
    ("status_code", "payload_bytes", "expose_status_attribute", "expected_alive"),
    [
        (200, b"true", True, True),
        (200, b"  ", True, True),
        (200, b"false", True, False),
        (503, b"true", True, False),
        (199, b"true", True, False),
        (204, b"TRUE", False, True),
    ],
)
def test_grobid_is_alive_interprets_probe_response(
    monkeypatch, status_code, payload_bytes, expose_status_attribute, expected_alive
):
    """Verify that grobid is alive interprets probe response."""
    requested_urls = []

    def fake_urlopen(request, timeout):
        requested_urls.append((request.full_url, timeout))
        return _FakeIsAliveResponse(
            status_code=status_code,
            payload_bytes=payload_bytes,
            expose_status_attribute=expose_status_attribute,
        )

    monkeypatch.setattr(grobid_runtime, "urlopen", fake_urlopen)
    assert grobid_runtime.grobid_is_alive("http://127.0.0.1:8070/") is expected_alive
    assert requested_urls == [("http://127.0.0.1:8070/api/isalive", 2.0)]


def test_grobid_is_alive_returns_false_when_probe_raises(monkeypatch):
    """Verify that grobid is alive returns false when probe raises."""

    def failing_urlopen(_request, timeout):
        raise OSError(f"connection refused after {timeout}")

    monkeypatch.setattr(grobid_runtime, "urlopen", failing_urlopen)
    assert grobid_runtime.grobid_is_alive("http://127.0.0.1:8070") is False


def test_grobid_container_name_and_image_prefer_biblicus_environment(monkeypatch):
    """Verify that grobid container name and image prefer biblicus environment."""
    monkeypatch.setenv("BIBLICUS_GROBID_CONTAINER_NAME", "biblicus-grobid")
    monkeypatch.setenv("PAPYRUS_GROBID_CONTAINER_NAME", "papyrus-other")
    monkeypatch.setenv("BIBLICUS_GROBID_DOCKER_IMAGE", "example/grobid:1")
    monkeypatch.setenv("PAPYRUS_GROBID_DOCKER_IMAGE", "example/grobid:2")
    assert grobid_runtime._grobid_container_name() == "biblicus-grobid"
    assert grobid_runtime._grobid_docker_image() == "example/grobid:1"


def test_grobid_container_name_and_image_use_papyrus_environment(monkeypatch):
    """Verify that grobid container name and image use papyrus environment."""
    monkeypatch.delenv("BIBLICUS_GROBID_CONTAINER_NAME", raising=False)
    monkeypatch.setenv("PAPYRUS_GROBID_CONTAINER_NAME", "papyrus-other")
    monkeypatch.delenv("BIBLICUS_GROBID_DOCKER_IMAGE", raising=False)
    monkeypatch.setenv("PAPYRUS_GROBID_DOCKER_IMAGE", "example/grobid:2")
    assert grobid_runtime._grobid_container_name() == "papyrus-other"
    assert grobid_runtime._grobid_docker_image() == "example/grobid:2"


def test_grobid_container_name_and_image_fall_back_to_defaults(monkeypatch):
    """Verify that grobid container name and image fall back to defaults."""
    for environment_name in (
        "BIBLICUS_GROBID_CONTAINER_NAME",
        "PAPYRUS_GROBID_CONTAINER_NAME",
        "BIBLICUS_GROBID_DOCKER_IMAGE",
        "PAPYRUS_GROBID_DOCKER_IMAGE",
    ):
        monkeypatch.delenv(environment_name, raising=False)
    assert grobid_runtime._grobid_container_name() == grobid_runtime.DEFAULT_GROBID_CONTAINER_NAME
    assert grobid_runtime._grobid_docker_image() == grobid_runtime.DEFAULT_GROBID_DOCKER_IMAGE


@pytest.mark.parametrize(("connect_result", "expected_open"), [(0, True), (111, False)])
def test_port_is_open_reports_socket_connection_result(monkeypatch, connect_result, expected_open):
    """Verify that port is open reports socket connection result."""
    recorded_socket_calls = []

    class FakeSocket:
        def __init__(self, family, kind):
            recorded_socket_calls.append(("create", family, kind))

        def settimeout(self, seconds):
            recorded_socket_calls.append(("timeout", seconds))

        def connect_ex(self, address):
            recorded_socket_calls.append(("connect", address))
            return connect_result

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    fake_socket_module = SimpleNamespace(
        socket=FakeSocket,
        AF_INET=grobid_runtime.socket.AF_INET,
        SOCK_STREAM=grobid_runtime.socket.SOCK_STREAM,
    )
    monkeypatch.setattr(grobid_runtime, "socket", fake_socket_module)
    assert grobid_runtime._port_is_open("127.0.0.1", 8070) is expected_open
    assert ("connect", ("127.0.0.1", 8070)) in recorded_socket_calls
    assert ("timeout", 1.0) in recorded_socket_calls


def _install_docker_command_and_ready_daemon(monkeypatch):
    monkeypatch.setattr(grobid_runtime, "_resolve_docker_command", lambda: "/usr/bin/docker")
    monkeypatch.setattr(grobid_runtime, "_ensure_docker_daemon_ready", lambda _command: None)
    monkeypatch.setenv("BIBLICUS_GROBID_CONTAINER_NAME", "test-grobid")
    monkeypatch.setenv("BIBLICUS_GROBID_DOCKER_IMAGE", "example/grobid:test")


def test_start_or_reuse_local_grobid_container_requires_docker_binary(monkeypatch):
    """Verify that start or reuse local grobid container requires docker binary."""
    monkeypatch.setattr(grobid_runtime, "_resolve_docker_command", lambda: None)
    with pytest.raises(RuntimeError, match="Docker binary was not found"):
        grobid_runtime._start_or_reuse_local_grobid_container(port=8070)


def test_start_or_reuse_local_grobid_container_reuses_running_container(monkeypatch):
    """Verify that start or reuse local grobid container reuses running container."""
    _install_docker_command_and_ready_daemon(monkeypatch)
    recording_subprocess = _RecordingSubprocess(
        [_completed_process(returncode=0, stdout="abc123\n")]
    )
    monkeypatch.setattr(grobid_runtime, "subprocess", recording_subprocess)
    grobid_runtime._start_or_reuse_local_grobid_container(port=8070)
    assert len(recording_subprocess.recorded_commands) == 1
    assert "name=^/test-grobid$" in recording_subprocess.recorded_commands[0]


def test_start_or_reuse_local_grobid_container_starts_existing_stopped_container(monkeypatch):
    """Verify that start or reuse local grobid container starts existing stopped container."""
    _install_docker_command_and_ready_daemon(monkeypatch)
    recording_subprocess = _RecordingSubprocess(
        [
            _completed_process(returncode=0, stdout=""),
            _completed_process(returncode=0, stdout="def456\n"),
            _completed_process(returncode=0),
        ]
    )
    monkeypatch.setattr(grobid_runtime, "subprocess", recording_subprocess)
    grobid_runtime._start_or_reuse_local_grobid_container(port=8070)
    assert recording_subprocess.recorded_commands[-1] == [
        "/usr/bin/docker",
        "start",
        "test-grobid",
    ]


def test_start_or_reuse_local_grobid_container_reports_failed_start_of_existing_container(
    monkeypatch,
):
    """Verify that start or reuse local grobid container reports failed start of existing container."""
    _install_docker_command_and_ready_daemon(monkeypatch)
    recording_subprocess = _RecordingSubprocess(
        [
            _completed_process(returncode=0, stdout=""),
            _completed_process(returncode=0, stdout="def456\n"),
            _completed_process(returncode=1, stdout="start output", stderr=None),
        ]
    )
    monkeypatch.setattr(grobid_runtime, "subprocess", recording_subprocess)
    with pytest.raises(RuntimeError, match="Failed to start existing GROBID container test-grobid"):
        grobid_runtime._start_or_reuse_local_grobid_container(port=8070)


def test_start_or_reuse_local_grobid_container_launches_new_container(monkeypatch):
    """Verify that start or reuse local grobid container launches new container."""
    _install_docker_command_and_ready_daemon(monkeypatch)
    recording_subprocess = _RecordingSubprocess(
        [
            _completed_process(returncode=0, stdout=""),
            _completed_process(returncode=0, stdout=""),
            _completed_process(returncode=0, stdout="newid\n"),
        ]
    )
    monkeypatch.setattr(grobid_runtime, "subprocess", recording_subprocess)
    grobid_runtime._start_or_reuse_local_grobid_container(port=9070)
    assert recording_subprocess.recorded_commands[-1] == [
        "/usr/bin/docker",
        "run",
        "-d",
        "--name",
        "test-grobid",
        "-p",
        "9070:8070",
        "example/grobid:test",
    ]


def test_start_or_reuse_local_grobid_container_reports_failed_launch(monkeypatch):
    """Verify that start or reuse local grobid container reports failed launch."""
    _install_docker_command_and_ready_daemon(monkeypatch)
    recording_subprocess = _RecordingSubprocess(
        [
            _completed_process(returncode=1, stdout=None),
            _completed_process(returncode=0, stdout=None),
            _completed_process(returncode=125, stderr="image not found"),
        ]
    )
    monkeypatch.setattr(grobid_runtime, "subprocess", recording_subprocess)
    with pytest.raises(RuntimeError, match="using example/grobid:test: image not found"):
        grobid_runtime._start_or_reuse_local_grobid_container(port=8070)


def test_await_grobid_ready_returns_when_port_open_and_alive(monkeypatch):
    """Verify that await grobid ready returns when port open and alive."""
    fake_clock = _FakeClock(step_seconds=1.0)
    probed_addresses = []
    monkeypatch.setattr(grobid_runtime, "time", fake_clock)

    def record_port_probe(host, port):
        probed_addresses.append((host, port))
        return True

    monkeypatch.setattr(grobid_runtime, "_port_is_open", record_port_probe)
    monkeypatch.setattr(grobid_runtime, "grobid_is_alive", lambda _url: True)
    grobid_runtime._await_grobid_ready("https://localhost")
    assert probed_addresses == [("localhost", 443)]
    assert fake_clock.slept_durations == []


def test_await_grobid_ready_retries_then_times_out(monkeypatch):
    """Verify that await grobid ready retries then times out."""
    fake_clock = _FakeClock(step_seconds=50.0)
    probed_addresses = []
    monkeypatch.setattr(grobid_runtime, "time", fake_clock)

    def record_closed_port_probe(host, port):
        probed_addresses.append((host, port))
        return False

    monkeypatch.setattr(grobid_runtime, "_port_is_open", record_closed_port_probe)
    with pytest.raises(RuntimeError, match="did not become ready"):
        grobid_runtime._await_grobid_ready("http:///no-host")
    assert probed_addresses == [("127.0.0.1", 80), ("127.0.0.1", 80)]
    assert fake_clock.slept_durations == [1.5, 1.5]


def test_resolve_docker_command_prefers_path_lookup(monkeypatch):
    """Verify that resolve docker command prefers path lookup."""
    monkeypatch.setattr(
        grobid_runtime, "shutil", SimpleNamespace(which=lambda _name: "/usr/bin/docker")
    )
    assert grobid_runtime._resolve_docker_command() == "/usr/bin/docker"


def test_resolve_docker_command_uses_first_existing_candidate_path(monkeypatch, tmp_path):
    """Verify that resolve docker command uses first existing candidate path."""
    existing_candidate = tmp_path / "docker"
    existing_candidate.write_text("", encoding="utf-8")
    monkeypatch.setattr(grobid_runtime, "shutil", SimpleNamespace(which=lambda _name: None))
    monkeypatch.setattr(
        grobid_runtime,
        "DOCKER_CANDIDATE_PATHS",
        (str(tmp_path / "missing-docker"), str(existing_candidate)),
    )
    assert grobid_runtime._resolve_docker_command() == str(existing_candidate)


def test_resolve_docker_command_returns_none_when_no_candidate_exists(monkeypatch, tmp_path):
    """Verify that resolve docker command returns none when no candidate exists."""
    monkeypatch.setattr(grobid_runtime, "shutil", SimpleNamespace(which=lambda _name: None))
    monkeypatch.setattr(
        grobid_runtime, "DOCKER_CANDIDATE_PATHS", (str(tmp_path / "missing-docker"),)
    )
    assert grobid_runtime._resolve_docker_command() is None


@pytest.mark.parametrize(("returncode", "expected_ready"), [(0, True), (1, False)])
def test_docker_daemon_ready_reflects_docker_info_exit_code(
    monkeypatch, returncode, expected_ready
):
    """Verify that docker daemon ready reflects docker info exit code."""
    recording_subprocess = _RecordingSubprocess([_completed_process(returncode=returncode)])
    monkeypatch.setattr(grobid_runtime, "subprocess", recording_subprocess)
    assert grobid_runtime._docker_daemon_ready("/usr/bin/docker") is expected_ready
    assert recording_subprocess.recorded_commands == [["/usr/bin/docker", "info"]]


def test_ensure_docker_daemon_ready_returns_when_daemon_already_ready(monkeypatch):
    """Verify that ensure docker daemon ready returns when daemon already ready."""
    monkeypatch.setattr(grobid_runtime, "_docker_daemon_ready", lambda _command: True)
    grobid_runtime._ensure_docker_daemon_ready("/usr/bin/docker")


def test_ensure_docker_daemon_ready_raises_on_non_darwin_platform(monkeypatch):
    """Verify that ensure docker daemon ready raises on non darwin platform."""
    monkeypatch.setattr(grobid_runtime, "_docker_daemon_ready", lambda _command: False)
    monkeypatch.setattr(grobid_runtime, "sys", SimpleNamespace(platform="linux"))
    with pytest.raises(RuntimeError, match="Docker daemon is not ready"):
        grobid_runtime._ensure_docker_daemon_ready("/usr/bin/docker")


def test_ensure_docker_daemon_ready_raises_on_darwin_without_docker_desktop(monkeypatch):
    """Verify that ensure docker daemon ready raises on darwin without docker desktop."""
    monkeypatch.setattr(grobid_runtime, "_docker_daemon_ready", lambda _command: False)
    monkeypatch.setattr(grobid_runtime, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(grobid_runtime, "Path", lambda _path: SimpleNamespace(exists=lambda: False))
    with pytest.raises(RuntimeError, match="Docker daemon is not ready"):
        grobid_runtime._ensure_docker_daemon_ready("/usr/bin/docker")


def test_ensure_docker_daemon_ready_launches_docker_desktop_and_waits(monkeypatch):
    """Verify that ensure docker daemon ready launches docker desktop and waits."""
    daemon_ready_answers = [False, False, True]
    recording_subprocess = _RecordingSubprocess([_completed_process(returncode=0)])
    fake_clock = _FakeClock(step_seconds=1.0)
    monkeypatch.setattr(
        grobid_runtime, "_docker_daemon_ready", lambda _command: daemon_ready_answers.pop(0)
    )
    monkeypatch.setattr(grobid_runtime, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(grobid_runtime, "Path", lambda _path: SimpleNamespace(exists=lambda: True))
    monkeypatch.setattr(grobid_runtime, "subprocess", recording_subprocess)
    monkeypatch.setattr(grobid_runtime, "time", fake_clock)
    grobid_runtime._ensure_docker_daemon_ready("/usr/bin/docker")
    assert recording_subprocess.recorded_commands == [["open", "-a", "Docker"]]
    assert fake_clock.slept_durations == [1.5]


def test_ensure_docker_daemon_ready_times_out_waiting_for_docker_desktop(monkeypatch):
    """Verify that ensure docker daemon ready times out waiting for docker desktop."""
    recording_subprocess = _RecordingSubprocess([_completed_process(returncode=0)])
    fake_clock = _FakeClock(step_seconds=60.0)
    monkeypatch.setattr(grobid_runtime, "_docker_daemon_ready", lambda _command: False)
    monkeypatch.setattr(grobid_runtime, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(grobid_runtime, "Path", lambda _path: SimpleNamespace(exists=lambda: True))
    monkeypatch.setattr(grobid_runtime, "subprocess", recording_subprocess)
    monkeypatch.setattr(grobid_runtime, "time", fake_clock)
    with pytest.raises(RuntimeError, match="Docker daemon is not ready"):
        grobid_runtime._ensure_docker_daemon_ready("/usr/bin/docker")
    assert fake_clock.slept_durations == [1.5]


def test_docker_lines_returns_empty_list_on_failure(monkeypatch):
    """Verify that docker lines returns empty list on failure."""
    recording_subprocess = _RecordingSubprocess(
        [_completed_process(returncode=1, stdout="ignored")]
    )
    monkeypatch.setattr(grobid_runtime, "subprocess", recording_subprocess)
    assert grobid_runtime._docker_lines("/usr/bin/docker", ["ps"]) == []


def test_docker_lines_returns_stripped_non_empty_lines(monkeypatch):
    """Verify that docker lines returns stripped non empty lines."""
    recording_subprocess = _RecordingSubprocess(
        [_completed_process(returncode=0, stdout=" first \n\n  second\n   \n")]
    )
    monkeypatch.setattr(grobid_runtime, "subprocess", recording_subprocess)
    assert grobid_runtime._docker_lines("/usr/bin/docker", ["ps", "-a"]) == ["first", "second"]
    assert recording_subprocess.recorded_commands == [["/usr/bin/docker", "ps", "-a"]]


@pytest.mark.parametrize(
    ("raw_value", "expected_limit"),
    [("not-a-number", 2), ("0", 1), ("5", 5)],
)
def test_grobid_max_concurrent_requests_parses_environment(monkeypatch, raw_value, expected_limit):
    """Verify that grobid max concurrent requests parses environment."""
    monkeypatch.setenv("BIBLICUS_GROBID_MAX_CONCURRENT", raw_value)
    assert grobid_client.grobid_max_concurrent_requests() == expected_limit


@pytest.mark.parametrize(
    ("raw_value", "expected_retries"),
    [("not-a-number", 3), ("-4", 1), ("6", 6)],
)
def test_grobid_max_retries_parses_environment(monkeypatch, raw_value, expected_retries):
    """Verify that grobid max retries parses environment."""
    monkeypatch.setenv("BIBLICUS_GROBID_MAX_RETRIES", raw_value)
    assert grobid_client.grobid_max_retries() == expected_retries


def test_grobid_semaphore_is_created_once_and_reused(monkeypatch):
    """Verify that grobid semaphore is created once and reused."""
    monkeypatch.setattr(grobid_client, "_GROBID_SEMAPHORE", None)
    first_semaphore = grobid_client._grobid_semaphore()
    assert grobid_client._grobid_semaphore() is first_semaphore


def test_is_retryable_grobid_error_rejects_non_transient_code():
    """Verify that is retryable grobid error rejects non transient code."""
    assert not grobid_client.is_retryable_grobid_error(
        UrlTextExtractionError(code="grobid_invalid_pdf", message="bad pdf")
    )


def test_is_retryable_grobid_error_accepts_http_error_without_status_details():
    """Verify that is retryable grobid error accepts http error without status details."""
    assert grobid_client.is_retryable_grobid_error(
        UrlTextExtractionError(code="grobid_http_error", message="unknown", details=None)
    )
    assert grobid_client.is_retryable_grobid_error(
        UrlTextExtractionError(code="grobid_http_error", message="unknown", details={})
    )


def _install_grobid_client_test_doubles(monkeypatch, *, max_retries):
    slept_backoffs = []
    monkeypatch.setenv("BIBLICUS_GROBID_MAX_RETRIES", str(max_retries))
    monkeypatch.setattr(grobid_client, "_GROBID_SEMAPHORE", None)
    monkeypatch.setattr(grobid_runtime, "ensure_grobid_running", lambda: None)
    monkeypatch.setattr(grobid_client.time, "sleep", slept_backoffs.append)
    return slept_backoffs


def test_call_grobid_with_limits_raises_immediately_for_non_retryable_error(monkeypatch):
    """Verify that call grobid with limits raises immediately for non retryable error."""
    slept_backoffs = _install_grobid_client_test_doubles(monkeypatch, max_retries=3)
    attempted_operations = []

    def failing_operation():
        attempted_operations.append("attempt")
        raise UrlTextExtractionError(code="grobid_invalid_pdf", message="bad pdf")

    with pytest.raises(UrlTextExtractionError, match="bad pdf"):
        grobid_client.call_grobid_with_limits(failing_operation)
    assert attempted_operations == ["attempt"]
    assert slept_backoffs == []


def test_call_grobid_with_limits_raises_after_exhausting_retries(monkeypatch):
    """Verify that call grobid with limits raises after exhausting retries."""
    slept_backoffs = _install_grobid_client_test_doubles(monkeypatch, max_retries=2)

    def always_unreachable_operation():
        raise UrlTextExtractionError(code="grobid_unreachable", message="down")

    with pytest.raises(UrlTextExtractionError, match="down"):
        grobid_client.call_grobid_with_limits(always_unreachable_operation)
    assert slept_backoffs == [0.75]


def test_call_grobid_with_limits_raises_generic_error_when_no_attempt_is_made(monkeypatch):
    """Verify that call grobid with limits raises generic error when no attempt is made."""
    _install_grobid_client_test_doubles(monkeypatch, max_retries=1)
    monkeypatch.setattr(grobid_client, "grobid_max_retries", lambda: 0)
    with pytest.raises(UrlTextExtractionError, match="GROBID request failed."):
        grobid_client.call_grobid_with_limits(lambda: "never called")
