"""
Neo4j graph storage helpers for Biblicus.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional

from ..user_config import BiblicusUserConfig, load_user_config


@dataclass(frozen=True)
class Neo4jSettings:
    """
    Configuration values for Neo4j connectivity and lifecycle.

    :ivar uri: Neo4j connection URI.
    :ivar username: Neo4j username.
    :ivar password: Neo4j password.
    :ivar database: Optional Neo4j database name.
    :ivar auto_start: Whether to auto-start Neo4j via Docker.
    :ivar container_name: Docker container name for auto-start.
    :ivar docker_image: Docker image for auto-start.
    :ivar http_port: HTTP port for Neo4j UI.
    :ivar bolt_port: Bolt port for Neo4j driver connections.
    """

    uri: str
    username: str
    password: str
    database: Optional[str]
    auto_start: bool
    container_name: str
    docker_image: str
    http_port: int
    bolt_port: int


def resolve_neo4j_settings(*, config: Optional[BiblicusUserConfig] = None) -> Neo4jSettings:
    """
    Resolve Neo4j settings from environment or user configuration.

    :param config: Optional pre-loaded user configuration.
    :type config: BiblicusUserConfig or None
    :return: Resolved Neo4j settings.
    :rtype: Neo4jSettings
    """
    loaded = config or load_user_config()
    neo4j_config = getattr(loaded, "neo4j", None)

    uri = os.environ.get("NEO4J_URI") or (neo4j_config.uri if neo4j_config else None)
    username = os.environ.get("NEO4J_USERNAME") or (
        neo4j_config.username if neo4j_config else None
    )
    password = os.environ.get("NEO4J_PASSWORD") or (
        neo4j_config.password if neo4j_config else None
    )
    database = os.environ.get("NEO4J_DATABASE") or (
        neo4j_config.database if neo4j_config else None
    )

    auto_start_env = os.environ.get("BIBLICUS_NEO4J_AUTO_START")
    if auto_start_env is not None:
        auto_start = auto_start_env.strip().lower() in {"1", "true", "yes", "on"}
    else:
        auto_start = neo4j_config.auto_start if neo4j_config else True

    container_name = os.environ.get("BIBLICUS_NEO4J_CONTAINER_NAME") or (
        neo4j_config.container_name if neo4j_config else "biblicus-neo4j"
    )
    docker_image = os.environ.get("BIBLICUS_NEO4J_IMAGE") or (
        neo4j_config.docker_image if neo4j_config else "neo4j:5"
    )

    http_port = _resolve_int(
        "BIBLICUS_NEO4J_HTTP_PORT",
        neo4j_config.http_port if neo4j_config else 7474,
    )
    bolt_port = _resolve_int(
        "BIBLICUS_NEO4J_BOLT_PORT",
        neo4j_config.bolt_port if neo4j_config else 7687,
    )

    resolved_uri = uri or f"bolt://localhost:{bolt_port}"
    resolved_username = username or "neo4j"
    resolved_password = password or "testpassword"

    return Neo4jSettings(
        uri=resolved_uri,
        username=resolved_username,
        password=resolved_password,
        database=database,
        auto_start=auto_start,
        container_name=container_name,
        docker_image=docker_image,
        http_port=http_port,
        bolt_port=bolt_port,
    )


def ensure_neo4j_running(settings: Neo4jSettings) -> None:
    """
    Ensure the Neo4j container is running when auto-start is enabled.

    :param settings: Resolved Neo4j settings.
    :type settings: Neo4jSettings
    :return: None.
    :rtype: None
    :raises ValueError: If Docker is unavailable or the container cannot be started.
    """
    if not settings.auto_start:
        return
    if shutil.which("docker") is None:
        raise ValueError("Neo4j auto-start requires Docker to be installed")
    if _container_running(settings.container_name):
        return
    if _container_exists(settings.container_name):
        _docker_start(settings.container_name)
    else:
        _docker_run(settings)


def create_neo4j_driver(settings: Neo4jSettings):
    """
    Create a Neo4j driver, waiting for availability when auto-start is enabled.

    :param settings: Resolved Neo4j settings.
    :type settings: Neo4jSettings
    :return: Neo4j driver instance.
    :rtype: neo4j.Driver
    :raises ValueError: If the Neo4j driver dependency is missing.
    """
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise ValueError(
            "Neo4j support requires an optional dependency. "
            'Install it with pip install "biblicus[neo4j]".'
        ) from exc

    ensure_neo4j_running(settings)

    driver = GraphDatabase.driver(
        settings.uri,
        auth=(settings.username, settings.password),
    )
    _wait_for_neo4j(driver, settings)
    return driver


def _wait_for_neo4j(driver, settings: Neo4jSettings) -> None:
    deadline = time.time() + 30
    last_error: Optional[Exception] = None
    while time.time() < deadline:
        try:
            with driver.session(database=settings.database) as session:
                session.run("RETURN 1")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
    message = "Neo4j did not become available within 30 seconds"
    if last_error is not None:
        message = f"{message}: {last_error}"
    raise ValueError(message)


def _resolve_int(env_key: str, default: int) -> int:
    raw = os.environ.get(env_key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{env_key} must be an integer") from exc


def _container_running(name: str) -> bool:
    output = _run_docker(
        ["ps", "--filter", f"name={name}", "--filter", "status=running", "--format", "{{.Names}}"]
    )
    return name in output.splitlines()


def _container_exists(name: str) -> bool:
    output = _run_docker(
        ["ps", "-a", "--filter", f"name={name}", "--format", "{{.Names}}"]
    )
    return name in output.splitlines()


def _docker_start(name: str) -> None:
    _run_docker(["start", name])


def _docker_run(settings: Neo4jSettings) -> None:
    args = [
        "run",
        "-d",
        "--name",
        settings.container_name,
        "-p",
        f"{settings.http_port}:7474",
        "-p",
        f"{settings.bolt_port}:7687",
        "-e",
        f"NEO4J_AUTH={settings.username}/{settings.password}",
        settings.docker_image,
    ]
    _run_docker(args)


def _run_docker(args: List[str]) -> str:
    result = subprocess.run(
        ["docker", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Docker command failed"
        raise ValueError(message)
    return result.stdout


def write_graph_records(
    *,
    driver,
    settings: Neo4jSettings,
    corpus_id: str,
    graph_id: str,
    extraction_snapshot: str,
    item_id: str,
    nodes,
    edges,
) -> None:
    """
    Persist graph nodes and edges to Neo4j.

    :param driver: Neo4j driver instance.
    :type driver: neo4j.Driver
    :param settings: Resolved Neo4j settings.
    :type settings: Neo4jSettings
    :param corpus_id: Corpus identifier.
    :type corpus_id: str
    :param graph_id: Graph identifier.
    :type graph_id: str
    :param extraction_snapshot: Extraction snapshot reference.
    :type extraction_snapshot: str
    :param item_id: Corpus item identifier.
    :type item_id: str
    :param nodes: Iterable of graph nodes.
    :type nodes: Iterable[biblicus.graph.models.GraphNode]
    :param edges: Iterable of graph edges.
    :type edges: Iterable[biblicus.graph.models.GraphEdge]
    :return: None.
    :rtype: None
    """
    node_payload = [
        {
            "node_id": node.node_id,
            "node_type": node.node_type,
            "label": node.label,
            "properties_json": json.dumps(node.properties, sort_keys=True),
        }
        for node in nodes
    ]
    edge_payload = [
        {
            "edge_id": edge.edge_id,
            "src": edge.src,
            "dst": edge.dst,
            "edge_type": edge.edge_type,
            "weight": edge.weight,
            "properties_json": json.dumps(edge.properties, sort_keys=True),
        }
        for edge in edges
    ]

    with driver.session(database=settings.database) as session:
        if node_payload:
            session.execute_write(
                _write_nodes,
                corpus_id,
                graph_id,
                extraction_snapshot,
                item_id,
                node_payload,
            )
        if edge_payload:
            session.execute_write(
                _write_edges,
                corpus_id,
                graph_id,
                extraction_snapshot,
                item_id,
                edge_payload,
            )


def _write_nodes(tx, corpus_id: str, graph_id: str, extraction_snapshot: str, item_id: str, nodes):
    tx.run(
        """
        UNWIND $nodes AS node
        MERGE (n:GraphNode {
            corpus_id: $corpus_id,
            graph_id: $graph_id,
            extraction_snapshot_id: $extraction_snapshot,
            item_id: $item_id,
            node_id: node.node_id
        })
        SET n.node_type = node.node_type,
            n.label = node.label,
            n.properties_json = node.properties_json
        """,
        corpus_id=corpus_id,
        graph_id=graph_id,
        extraction_snapshot=extraction_snapshot,
        item_id=item_id,
        nodes=nodes,
    )


def clear_graph_records(
    *,
    driver,
    settings: Neo4jSettings,
    corpus_id: str,
    graph_id: str,
    extraction_snapshot: str,
) -> None:
    """
    Remove graph nodes and edges for a corpus graph snapshot.

    :param driver: Neo4j driver instance.
    :param settings: Resolved Neo4j settings.
    :param corpus_id: Corpus identifier.
    :param graph_id: Graph identifier.
    :param extraction_snapshot: Extraction snapshot reference string.
    """
    with driver.session(database=settings.database) as session:
        session.execute_write(
            _clear_graph_records,
            corpus_id,
            graph_id,
            extraction_snapshot,
        )


def read_graph_records(
    *,
    driver,
    settings: Neo4jSettings,
    corpus_id: str,
    graph_id: str,
    extraction_snapshot: str,
) -> dict[str, list[dict[str, object]]]:
    """
    Read graph nodes and edges for a corpus graph snapshot from Neo4j.

    :return: Mapping with ``nodes`` and ``edges`` record lists.
    """
    with driver.session(database=settings.database) as session:
        node_rows = session.execute_read(
            _read_nodes,
            corpus_id,
            graph_id,
            extraction_snapshot,
        )
        edge_rows = session.execute_read(
            _read_edges,
            corpus_id,
            graph_id,
            extraction_snapshot,
        )
    return {"nodes": node_rows, "edges": edge_rows}


def _clear_graph_records(tx, corpus_id: str, graph_id: str, extraction_snapshot: str) -> None:
    tx.run(
        """
        MATCH ()-[r:RELATED {
            corpus_id: $corpus_id,
            graph_id: $graph_id,
            extraction_snapshot_id: $extraction_snapshot
        }]->()
        DELETE r
        """,
        corpus_id=corpus_id,
        graph_id=graph_id,
        extraction_snapshot=extraction_snapshot,
    )
    tx.run(
        """
        MATCH (n:GraphNode {
            corpus_id: $corpus_id,
            graph_id: $graph_id,
            extraction_snapshot_id: $extraction_snapshot
        })
        DELETE n
        """,
        corpus_id=corpus_id,
        graph_id=graph_id,
        extraction_snapshot=extraction_snapshot,
    )


def _read_nodes(tx, corpus_id: str, graph_id: str, extraction_snapshot: str) -> list[dict[str, object]]:
    result = tx.run(
        """
        MATCH (n:GraphNode {
            corpus_id: $corpus_id,
            graph_id: $graph_id,
            extraction_snapshot_id: $extraction_snapshot
        })
        RETURN n.item_id AS item_id,
               n.node_id AS node_id,
               n.node_type AS node_type,
               n.label AS label,
               n.properties_json AS properties_json
        ORDER BY item_id, node_id
        """,
        corpus_id=corpus_id,
        graph_id=graph_id,
        extraction_snapshot=extraction_snapshot,
    )
    rows: list[dict[str, object]] = []
    for record in result:
        properties_raw = record.get("properties_json")
        try:
            properties = json.loads(properties_raw) if properties_raw else {}
        except json.JSONDecodeError:
            properties = {}
        if not isinstance(properties, dict):
            properties = {}
        rows.append(
            {
                "item_id": record["item_id"],
                "node_id": record["node_id"],
                "node_type": record["node_type"],
                "label": record["label"],
                "properties": properties,
            }
        )
    return rows


def _read_edges(tx, corpus_id: str, graph_id: str, extraction_snapshot: str) -> list[dict[str, object]]:
    result = tx.run(
        """
        MATCH ()-[r:RELATED {
            corpus_id: $corpus_id,
            graph_id: $graph_id,
            extraction_snapshot_id: $extraction_snapshot
        }]->()
        RETURN r.item_id AS item_id,
               r.edge_id AS edge_id,
               startNode(r).node_id AS src,
               endNode(r).node_id AS dst,
               r.edge_type AS edge_type,
               r.weight AS weight,
               r.properties_json AS properties_json
        ORDER BY item_id, edge_id
        """,
        corpus_id=corpus_id,
        graph_id=graph_id,
        extraction_snapshot=extraction_snapshot,
    )
    rows: list[dict[str, object]] = []
    for record in result:
        properties_raw = record.get("properties_json")
        try:
            properties = json.loads(properties_raw) if properties_raw else {}
        except json.JSONDecodeError:
            properties = {}
        if not isinstance(properties, dict):
            properties = {}
        rows.append(
            {
                "item_id": record["item_id"],
                "edge_id": record["edge_id"],
                "src": record["src"],
                "dst": record["dst"],
                "edge_type": record["edge_type"],
                "weight": record.get("weight", 1.0),
                "properties": properties,
            }
        )
    return rows


def _write_edges(
    tx, corpus_id: str, graph_id: str, extraction_snapshot: str, item_id: str, edges
):
    tx.run(
        """
        UNWIND $edges AS edge
        MATCH (src:GraphNode {
            corpus_id: $corpus_id,
            graph_id: $graph_id,
            extraction_snapshot_id: $extraction_snapshot,
            item_id: $item_id,
            node_id: edge.src
        })
        MATCH (dst:GraphNode {
            corpus_id: $corpus_id,
            graph_id: $graph_id,
            extraction_snapshot_id: $extraction_snapshot,
            item_id: $item_id,
            node_id: edge.dst
        })
        MERGE (src)-[r:RELATED {
            corpus_id: $corpus_id,
            graph_id: $graph_id,
            extraction_snapshot_id: $extraction_snapshot,
            item_id: $item_id,
            edge_id: edge.edge_id
        }]->(dst)
        SET r.edge_type = edge.edge_type,
            r.weight = edge.weight,
            r.properties_json = edge.properties_json
        """,
        corpus_id=corpus_id,
        graph_id=graph_id,
        extraction_snapshot=extraction_snapshot,
        item_id=item_id,
        edges=edges,
    )
