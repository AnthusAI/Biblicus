# Taxonomy and ontology graph steering

## Press release

Biblicus now accepts a reviewed taxonomy from an external steering application, validates it as a strict tree, and uses
that taxonomy to steer GraphRAG graph materialization. The taxonomy gives editors a durable topic hierarchy while the
ontology layer records explicit directed relationships between topics, items, and graph entities.

Graph extraction remains a rebuildable analysis step. Accepted taxonomy and ontology state is only written into Neo4j
when a worker explicitly runs ontology materialization.

## Frequently asked questions

### Why add taxonomy when Biblicus already has topic classifiers?

Topic classifiers provide stable topic identities, but they are flat. A taxonomy gives those identities reviewed parent
and child structure without making BERTopic integer topic ids part of the public contract.

### Is the taxonomy the graph?

No. The accepted taxonomy is a strict tree. The ontology is a graph of explicit relationship assertions. Neo4j is a
materialized GraphRAG projection of graph extraction, taxonomy nodes, taxonomy edges, and accepted ontology assertions.

### Who owns accepted human decisions?

The external steering application owns human decisions. Biblicus validates and records accepted exports, creates
discovery signals and proposal artifacts, and materializes accepted state when asked.

### Does taxonomy discovery mutate the accepted taxonomy?

No. Discovery emits computational signals and proposal judgments only. Accepted taxonomy changes arrive later as a new
external app export.

### Why is graph materialization explicit?

Explicit materialization keeps graph extraction reproducible and prevents accepted ontology state from being silently
mixed into exploratory graph snapshots.

### What is the first worker workflow?

1. Export an accepted taxonomy from the steering application.
2. Run `biblicus taxonomy record --corpus <path> --input taxonomy.json`.
3. Optionally run `biblicus taxonomy discover` to produce proposed child-topic changes.
4. Export accepted ontology relationship assertions from the steering application.
5. Run `biblicus ontology record --corpus <path> --input ontology.json`.
6. Run `biblicus ontology apply --corpus <path> --taxonomy <snapshot_id> --relationships <snapshot_id> --graph-snapshot <extractor:snapshot>`.
