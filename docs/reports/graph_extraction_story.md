# Graph extraction integration report

In this run, Biblicus downloaded 5 Wikipedia items into /Users/ryan.porter/Projects/Biblicus/corpora/wiki_graph_demo, built extraction snapshot pipeline:add0d35731fabde3b6d9b24d4adceb68f7aa9187ca43a8e0e3354b13309c8bb1, and materialized graph snapshot c879b092c73cd9f000fb2d4e5683aa3329f663188e57de8b0409e0eb73dfcc20 as graph simple-entities:dd52d74864691af27671b0f0ce73925b5e8812d60b3b10da6cd3c0808a4203f3. Neo4j reports 39 nodes and 83 edges. Sample entities include Ada Lovelace, Alan Mathison Turing, Alan Turing, Alongside, Alonzo Church.

## What worked

- Wikipedia corpus downloaded and ingested.
- Extraction snapshot built successfully.
- Graph snapshot materialized to Neo4j.
- Neo4j reports 39 nodes and 83 edges.

## What did not work

- No known failures observed in this run.

## Next steps

- Decide whether to store graph properties as native Neo4j maps or JSON strings.
- Add a graph-aware retriever that consumes the materialized graph.
- Expand integration runs with a larger corpus for richer graphs.

## Run details

- Corpus: `/Users/ryan.porter/Projects/Biblicus/corpora/wiki_graph_demo`
- Extraction snapshot: `pipeline:add0d35731fabde3b6d9b24d4adceb68f7aa9187ca43a8e0e3354b13309c8bb1`
- Graph snapshot: `c879b092c73cd9f000fb2d4e5683aa3329f663188e57de8b0409e0eb73dfcc20`
- Graph id: `simple-entities:dd52d74864691af27671b0f0ce73925b5e8812d60b3b10da6cd3c0808a4203f3`
- Neo4j nodes: `39`
- Neo4j edges: `83`

## Sample entities

Ada Lovelace, Alan Mathison Turing, Alan Turing, Alongside, Alonzo Church

## Latest demo run

Command:
python scripts/graph_extraction_integration.py --corpus corpora/wiki_graph_demo --force --verify --limit 5 --report-path reports/graph_extraction_story.md

Result summary:
- 5 items ingested
- Neo4j counts: 39 nodes / 83 edges
- Sample entities: Ada Lovelace, Alan Mathison Turing, Alan Turing, Alongside, Alonzo Church

