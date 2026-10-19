from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List

import pytest

from biblicus.graph import neo4j as graph_neo4j
from biblicus.graph.models import GraphEdge, GraphNode
from biblicus.graph.neo4j import (
    Neo4jSettings,
    clear_graph_records,
    create_neo4j_driver,
    ensure_neo4j_running,
    read_graph_records,
    resolve_neo4j_settings,
    write_graph_records,
)
from biblicus.user_config import BiblicusUserConfig, Neo4jUserConfig

NEO4J_ENVIRONMENT_KEYS = [
    "NEO4J_URI",
    "NEO4J_USERNAME",
    "NEO4J_PASSWORD",
    "NEO4J_DATABASE",
    "BIBLICUS_NEO4J_AUTO_START",
    "BIBLICUS_NEO4J_CONTAINER_NAME",
    "BIBLICUS_NEO4J_IMAGE",
    "BIBLICUS_NEO4J_HTTP_PORT",
    "BIBLICUS_NEO4J_BOLT_PORT",
]


@pytest.fixture
def clean_neo4j_environment(monkeypatch):
    """Return monkeypatch after clearing Neo4j environment variables."""
    for key in NEO4J_ENVIRONMENT_KEYS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def build_settings(**overrides: Any) -> Neo4jSettings:
    """Build settings."""
    values: Dict[str, Any] = dict(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="secret",
        database="graphdb",
        auto_start=True,
        container_name="biblicus-neo4j",
        docker_image="neo4j:5",
        http_port=7474,
        bolt_port=7687,
    )
    values.update(overrides)
    return Neo4jSettings(**values)


class RecordingTransaction:
    """Test double: recording transaction."""

    def __init__(self, results: List[List[Dict[str, Any]]] | None = None) -> None:
        self.runs: List[tuple[str, Dict[str, Any]]] = []
        self.results = list(results or [])

    def run(self, query: str, **parameters: Any):
        """Record a query and return the next scripted result."""
        self.runs.append((query, parameters))
        return self.results.pop(0) if self.results else []


class RecordingSession:
    """Test double: recording session."""

    def __init__(self, transaction: RecordingTransaction) -> None:
        self.transaction = transaction
        self.write_functions: List[Any] = []
        self.read_functions: List[Any] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute_write(self, function, *arguments):
        """Run a write function against the recording transaction."""
        self.write_functions.append(function)
        return function(self.transaction, *arguments)

    def execute_read(self, function, *arguments):
        """Run a read function against the recording transaction."""
        self.read_functions.append(function)
        return function(self.transaction, *arguments)

    def run(self, query: str):
        """Record a query and return the next scripted result."""
        return self.transaction.run(query)


class RecordingDriver:
    """Test double: recording driver."""

    def __init__(self, transaction: RecordingTransaction) -> None:
        self.session_instance = RecordingSession(transaction)
        self.databases: List[Any] = []

    def session(self, database=None):
        """Return the recording session for the requested database."""
        self.databases.append(database)
        return self.session_instance


def test_resolve_neo4j_settings_uses_defaults_without_configuration(
    clean_neo4j_environment,
):
    """Verify resolve neo4j settings uses defaults without configuration."""
    settings = resolve_neo4j_settings(config=BiblicusUserConfig())

    assert settings == Neo4jSettings(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="testpassword",
        database=None,
        auto_start=True,
        container_name="biblicus-neo4j",
        docker_image="neo4j:5",
        http_port=7474,
        bolt_port=7687,
    )


def test_resolve_neo4j_settings_loads_user_configuration_when_not_provided(
    clean_neo4j_environment,
):
    """Verify resolve neo4j settings loads user configuration when not provided."""
    loaded_configuration = BiblicusUserConfig(
        neo4j=Neo4jUserConfig(
            uri="bolt://configured:9999",
            username="configured-user",
            password="configured-password",
            database="configured-db",
            auto_start=False,
            container_name="configured-container",
            docker_image="neo4j:configured",
            http_port=1111,
            bolt_port=2222,
        )
    )
    clean_neo4j_environment.setattr(graph_neo4j, "load_user_config", lambda: loaded_configuration)

    settings = resolve_neo4j_settings()

    assert settings.uri == "bolt://configured:9999"
    assert settings.username == "configured-user"
    assert settings.password == "configured-password"
    assert settings.database == "configured-db"
    assert settings.auto_start is False
    assert settings.container_name == "configured-container"
    assert settings.docker_image == "neo4j:configured"
    assert settings.http_port == 1111
    assert settings.bolt_port == 2222


def test_resolve_neo4j_settings_prefers_environment_variables(clean_neo4j_environment):
    """Verify resolve neo4j settings prefers environment variables."""
    environment = {
        "NEO4J_USERNAME": "env-user",
        "NEO4J_PASSWORD": "env-password",
        "NEO4J_DATABASE": "env-db",
        "BIBLICUS_NEO4J_AUTO_START": " Off ",
        "BIBLICUS_NEO4J_CONTAINER_NAME": "env-container",
        "BIBLICUS_NEO4J_IMAGE": "neo4j:env",
        "BIBLICUS_NEO4J_HTTP_PORT": "17474",
        "BIBLICUS_NEO4J_BOLT_PORT": "17687",
    }
    for key, value in environment.items():
        clean_neo4j_environment.setenv(key, value)

    settings = resolve_neo4j_settings(
        config=BiblicusUserConfig(neo4j=Neo4jUserConfig(auto_start=True))
    )

    assert settings.uri == "bolt://localhost:17687"
    assert settings.username == "env-user"
    assert settings.password == "env-password"
    assert settings.database == "env-db"
    assert settings.auto_start is False
    assert settings.container_name == "env-container"
    assert settings.docker_image == "neo4j:env"
    assert settings.http_port == 17474
    assert settings.bolt_port == 17687


def test_resolve_neo4j_settings_accepts_truthy_auto_start_and_explicit_uri(
    clean_neo4j_environment,
):
    """Verify resolve neo4j settings accepts truthy auto start and explicit uri."""
    clean_neo4j_environment.setenv("BIBLICUS_NEO4J_AUTO_START", "yes")
    clean_neo4j_environment.setenv("NEO4J_URI", "bolt://explicit:7687")

    settings = resolve_neo4j_settings(config=BiblicusUserConfig())

    assert settings.auto_start is True
    assert settings.uri == "bolt://explicit:7687"


def test_resolve_neo4j_settings_rejects_non_integer_port(clean_neo4j_environment):
    """Verify resolve neo4j settings rejects non integer port."""
    clean_neo4j_environment.setenv("BIBLICUS_NEO4J_HTTP_PORT", "not-a-port")

    with pytest.raises(ValueError, match="BIBLICUS_NEO4J_HTTP_PORT must be an integer"):
        resolve_neo4j_settings(config=BiblicusUserConfig())


def install_fake_docker(monkeypatch, responses: Dict[str, SimpleNamespace]) -> List[List[str]]:
    """Install fake docker."""
    invocations: List[List[str]] = []

    def fake_subprocess_run(command, check, capture_output, text):
        """Record the Docker command and return a scripted result."""
        invocations.append(command)
        return responses[command[1]]

    monkeypatch.setattr(graph_neo4j.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(graph_neo4j.subprocess, "run", fake_subprocess_run)
    return invocations


def docker_result(stdout: str = "", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    """Return a fake completed Docker process result."""
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_ensure_neo4j_running_does_nothing_when_auto_start_disabled(monkeypatch):
    """Verify ensure neo4j running does nothing when auto start disabled."""
    monkeypatch.setattr(
        graph_neo4j.shutil, "which", lambda name: pytest.fail("docker lookup not expected")
    )

    assert ensure_neo4j_running(build_settings(auto_start=False)) is None


def test_ensure_neo4j_running_requires_docker(monkeypatch):
    """Verify ensure neo4j running requires docker."""
    monkeypatch.setattr(graph_neo4j.shutil, "which", lambda name: None)

    with pytest.raises(ValueError, match="requires Docker"):
        ensure_neo4j_running(build_settings())


def test_ensure_neo4j_running_returns_when_container_already_running(monkeypatch):
    """Verify ensure neo4j running returns when container already running."""
    invocations = install_fake_docker(
        monkeypatch, {"ps": docker_result(stdout="other\nbiblicus-neo4j\n")}
    )

    ensure_neo4j_running(build_settings())

    assert len(invocations) == 1
    assert "status=running" in invocations[0]


def test_ensure_neo4j_running_starts_existing_stopped_container(monkeypatch):
    """Verify ensure neo4j running starts existing stopped container."""
    ps_outputs = iter([docker_result(stdout=""), docker_result(stdout="biblicus-neo4j\n")])
    invocations: List[List[str]] = []

    def fake_subprocess_run(command, check, capture_output, text):
        """Record the Docker command and return a scripted result."""
        invocations.append(command)
        if command[1] == "ps":
            return next(ps_outputs)
        return docker_result(stdout="biblicus-neo4j\n")

    monkeypatch.setattr(graph_neo4j.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(graph_neo4j.subprocess, "run", fake_subprocess_run)

    ensure_neo4j_running(build_settings())

    assert invocations[-1] == ["docker", "start", "biblicus-neo4j"]


def test_ensure_neo4j_running_runs_new_container_when_missing(monkeypatch):
    """Verify ensure neo4j running runs new container when missing."""
    invocations = install_fake_docker(
        monkeypatch,
        {"ps": docker_result(stdout=""), "run": docker_result(stdout="container-id\n")},
    )

    ensure_neo4j_running(build_settings(http_port=17474, bolt_port=17687))

    assert invocations[-1] == [
        "docker",
        "run",
        "-d",
        "--name",
        "biblicus-neo4j",
        "-p",
        "17474:7474",
        "-p",
        "17687:7687",
        "-e",
        "NEO4J_AUTH=neo4j/secret",
        "neo4j:5",
    ]


@pytest.mark.parametrize(
    "failed_result, expected_message",
    [
        (docker_result(stderr="daemon unavailable\n", returncode=1), "daemon unavailable"),
        (docker_result(stdout="stdout failure\n", returncode=1), "stdout failure"),
        (docker_result(returncode=1), "Docker command failed"),
    ],
)
def test_run_docker_reports_failure_message(monkeypatch, failed_result, expected_message):
    """Verify run docker reports failure message."""
    install_fake_docker(monkeypatch, {"ps": failed_result})

    with pytest.raises(ValueError, match=expected_message):
        ensure_neo4j_running(build_settings())


def install_fake_neo4j_module(monkeypatch, driver_factory) -> List[Dict[str, Any]]:
    """Install fake neo4j module."""
    driver_requests: List[Dict[str, Any]] = []
    fake_module = ModuleType("neo4j")

    class FakeGraphDatabase:
        """Test double: fake graph database."""

        @staticmethod
        def driver(uri, auth):
            """Return a driver from the configured factory."""
            driver_requests.append({"uri": uri, "auth": auth})
            return driver_factory()

    fake_module.GraphDatabase = FakeGraphDatabase
    monkeypatch.setitem(sys.modules, "neo4j", fake_module)
    return driver_requests


def test_create_neo4j_driver_requires_optional_dependency(monkeypatch):
    """Verify create neo4j driver requires optional dependency."""
    monkeypatch.setitem(sys.modules, "neo4j", None)

    with pytest.raises(ValueError, match="biblicus\\[neo4j\\]"):
        create_neo4j_driver(build_settings(auto_start=False))


def test_create_neo4j_driver_waits_until_session_succeeds(monkeypatch):
    """Verify create neo4j driver waits until session succeeds."""
    transaction = RecordingTransaction()
    driver = RecordingDriver(transaction)
    driver_requests = install_fake_neo4j_module(monkeypatch, lambda: driver)

    created = create_neo4j_driver(build_settings(auto_start=False))

    assert created is driver
    assert driver_requests == [{"uri": "bolt://localhost:7687", "auth": ("neo4j", "secret")}]
    assert transaction.runs == [("RETURN 1", {})]
    assert driver.databases == ["graphdb"]


class FakeClock:
    """Test double: fake clock."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: List[float] = []

    def time(self) -> float:
        """Return the fake current time."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Advance the fake clock past the requested delay."""
        self.sleeps.append(seconds)
        self.now += 20.0


class UnavailableDriver:
    """Test double: unavailable driver."""

    def session(self, database=None):
        """Return the recording session for the requested database."""
        raise ConnectionError("connection refused")


def test_wait_for_neo4j_retries_then_reports_last_error(monkeypatch):
    """Verify wait for neo4j retries then reports last error."""
    fake_clock = FakeClock()
    monkeypatch.setattr(graph_neo4j, "time", fake_clock)

    with pytest.raises(ValueError, match="within 30 seconds: connection refused"):
        graph_neo4j._wait_for_neo4j(UnavailableDriver(), build_settings())

    assert fake_clock.sleeps == [0.5, 0.5]


def test_wait_for_neo4j_reports_timeout_without_attempts(monkeypatch):
    """Verify wait for neo4j reports timeout without attempts."""
    clock_values = iter([1000.0, 2000.0])
    monkeypatch.setattr(
        graph_neo4j,
        "time",
        SimpleNamespace(time=lambda: next(clock_values), sleep=lambda seconds: None),
    )

    with pytest.raises(ValueError) as raised:
        graph_neo4j._wait_for_neo4j(UnavailableDriver(), build_settings())

    assert str(raised.value) == "Neo4j did not become available within 30 seconds"


def test_write_graph_records_writes_nodes_and_edges_with_serialized_properties():
    """Verify write graph records writes nodes and edges with serialized properties."""
    transaction = RecordingTransaction()
    driver = RecordingDriver(transaction)

    write_graph_records(
        driver=driver,
        settings=build_settings(),
        corpus_id="corpus",
        graph_id="graph",
        extraction_snapshot="pipeline:snap",
        item_id="item",
        nodes=[
            GraphNode(node_id="n1", node_type="entity", label="Alpha", properties={"b": 2, "a": 1})
        ],
        edges=[
            GraphEdge(
                edge_id="e1",
                src="n1",
                dst="n1",
                edge_type="self",
                weight=2.5,
                properties={"source": "test"},
            )
        ],
    )

    assert len(transaction.runs) == 2
    node_query, node_parameters = transaction.runs[0]
    assert "MERGE (n:GraphNode" in node_query
    assert node_parameters["nodes"][0]["properties_json"] == '{"a": 1, "b": 2}'
    edge_query, edge_parameters = transaction.runs[1]
    assert "MERGE (src)-[r:RELATED" in edge_query
    assert edge_parameters["edges"][0]["weight"] == 2.5
    assert edge_parameters["item_id"] == "item"


def test_write_graph_records_writes_only_nodes_when_no_edges():
    """Verify write graph records writes only nodes when no edges."""
    transaction = RecordingTransaction()
    driver = RecordingDriver(transaction)

    write_graph_records(
        driver=driver,
        settings=build_settings(),
        corpus_id="corpus",
        graph_id="graph",
        extraction_snapshot="pipeline:snap",
        item_id="item",
        nodes=[GraphNode(node_id="n1", node_type="entity", label="Alpha")],
        edges=[],
    )

    assert driver.session_instance.write_functions == [graph_neo4j._write_nodes]


def test_write_graph_records_writes_only_edges_when_no_nodes():
    """Verify write graph records writes only edges when no nodes."""
    transaction = RecordingTransaction()
    driver = RecordingDriver(transaction)

    write_graph_records(
        driver=driver,
        settings=build_settings(),
        corpus_id="corpus",
        graph_id="graph",
        extraction_snapshot="pipeline:snap",
        item_id="item",
        nodes=[],
        edges=[GraphEdge(edge_id="e1", src="a", dst="b", edge_type="mentions")],
    )

    assert driver.session_instance.write_functions == [graph_neo4j._write_edges]


def test_clear_graph_records_deletes_relationships_then_nodes():
    """Verify clear graph records deletes relationships then nodes."""
    transaction = RecordingTransaction()
    driver = RecordingDriver(transaction)

    clear_graph_records(
        driver=driver,
        settings=build_settings(database=None),
        corpus_id="corpus",
        graph_id="graph",
        extraction_snapshot="pipeline:snap",
    )

    assert len(transaction.runs) == 2
    assert "DELETE r" in transaction.runs[0][0]
    assert "DELETE n" in transaction.runs[1][0]
    assert transaction.runs[1][1] == {
        "corpus_id": "corpus",
        "graph_id": "graph",
        "extraction_snapshot": "pipeline:snap",
    }
    assert driver.databases == [None]


def test_read_graph_records_parses_properties_defensively():
    """Verify read graph records parses properties defensively."""
    node_records = [
        {
            "item_id": "item",
            "node_id": "n-valid",
            "node_type": "entity",
            "label": "Valid",
            "properties_json": json.dumps({"canonical": "valid"}),
        },
        {
            "item_id": "item",
            "node_id": "n-empty",
            "node_type": "entity",
            "label": "Empty",
            "properties_json": None,
        },
        {
            "item_id": "item",
            "node_id": "n-corrupt",
            "node_type": "entity",
            "label": "Corrupt",
            "properties_json": "{broken",
        },
        {
            "item_id": "item",
            "node_id": "n-list",
            "node_type": "entity",
            "label": "List",
            "properties_json": "[1, 2]",
        },
    ]
    edge_records = [
        {
            "item_id": "item",
            "edge_id": "e-valid",
            "src": "a",
            "dst": "b",
            "edge_type": "mentions",
            "weight": 4.0,
            "properties_json": json.dumps({"source": "test"}),
        },
        {
            "item_id": "item",
            "edge_id": "e-default-weight",
            "src": "a",
            "dst": "b",
            "edge_type": "mentions",
            "properties_json": "",
        },
        {
            "item_id": "item",
            "edge_id": "e-corrupt",
            "src": "a",
            "dst": "b",
            "edge_type": "mentions",
            "weight": 1.0,
            "properties_json": "{broken",
        },
        {
            "item_id": "item",
            "edge_id": "e-scalar",
            "src": "a",
            "dst": "b",
            "edge_type": "mentions",
            "weight": 1.0,
            "properties_json": "7",
        },
    ]
    transaction = RecordingTransaction(results=[node_records, edge_records])
    driver = RecordingDriver(transaction)

    records = read_graph_records(
        driver=driver,
        settings=build_settings(),
        corpus_id="corpus",
        graph_id="graph",
        extraction_snapshot="pipeline:snap",
    )

    assert [node["properties"] for node in records["nodes"]] == [
        {"canonical": "valid"},
        {},
        {},
        {},
    ]
    assert [edge["properties"] for edge in records["edges"]] == [{"source": "test"}, {}, {}, {}]
    assert records["edges"][1]["weight"] == 1.0
    assert records["edges"][0]["weight"] == 4.0
    assert "RETURN n.item_id" in transaction.runs[0][0]
    assert "startNode(r).node_id" in transaction.runs[1][0]
    assert driver.session_instance.read_functions == [
        graph_neo4j._read_nodes,
        graph_neo4j._read_edges,
    ]
