Biblicus
========

You have a folder full of files. Nobody knows what is in it. Someone wants answers anyway.

Biblicus is a Python toolkit that turns unstructured data into something you can manage, search,
analyze, and reuse. It supports end-to-end pipelines: ingest and extract content from mixed file
types, transform text with reusable AI utilities, retrieve evidence into model-friendly context,
and evaluate results so improvements are measurable.

Common, believable scenarios look like this:

- You inherit a huge archive of emails and need to build an assistant that can answer questions
  while protecting sensitive details.
- You receive a legal discovery dump of scanned PDFs and need to search, summarize, and trace
  evidence across thousands of pages.
- You need to make a policy or rules folder usable inside an AI system even though the source
  materials are far larger than any model context window.

If you have ever built a one-off script to “just get this data into shape”, Biblicus is the
version of that work you can keep: structured, repeatable, and designed for experimentation.

The project emphasizes evidence-first results, explicit retrieval stages, and evaluation so you
can defend what was retrieved, from where, and why.

Try It
------

If you want to decide quickly whether Biblicus is useful, run a tutorial. Each tutorial is a
small script that produces concrete output, and each one is covered by behavior specs so we do
not publish “works on my machine” examples.

Three good starting points:

**Notes to context**

Take a handful of short notes and turn them into a token-budgeted context pack you can paste
into a model request.

See :doc:`Notes to Context Pack <use_cases/notes_to_context_pack>`.

.. code-block:: bash

   python scripts/use_cases/notes_to_context_pack_demo.py \
     --corpus corpora/tutorial_notes_to_context_pack \
     --force

**Folder search**

Ingest a folder of text files, build a deterministic index, and retrieve evidence with
provenance.

See :doc:`Folder Search With Extraction <use_cases/text_folder_search>`.

.. code-block:: bash

   python scripts/use_cases/text_folder_search_demo.py \
     --corpus corpora/tutorial_text_folder_search \
     --force

**Sensitive text marking (mock + real API)**

Mark sensitive spans in a document using an agentic text utility. Run it in deterministic mock
mode first, then switch to a real model when you are ready.

See :doc:`Mark Sensitive Text for Redaction <use_cases/text_redact>`.

.. code-block:: bash

   python scripts/use_cases/text_redact_demo.py \
     --corpus corpora/tutorial_text_redact \
     --force \
     --mock

If your data has an inherent sequence (threads, transcripts, recurring phases), Markov analysis
adds a sequence model on top of segmented text. See :doc:`Sequence Graph With Markov Analysis <use_cases/sequence_markov>`.

.. toctree::
   :maxdepth: 1
   :caption: Tutorials

   USE_CASES

Learn the Concepts
------------------

If you want the mental model before running anything, start with data collections and extraction,
then move into retrieval and analysis. The rest of the documentation expands those foundations
into deeper evaluation and tooling.

Biblicus uses a small set of domain terms in its docs. The most important one is *corpus*
(plural: *corpora*): a managed folder on disk that holds raw items plus lightweight metadata.

.. toctree::
   :maxdepth: 1
   :caption: Concepts

   CORPUS
   EXTRACTION
   RETRIEVAL
   ANALYSIS

Core Building Blocks
--------------------

These pages define the vocabulary and invariants that keep Biblicus stable across backends and
recipes. Read them when you want to understand *what is a corpus*, *what is evidence*, and *what
stays the same even when the pipeline changes*.

.. toctree::
   :maxdepth: 2
   :caption: Core Building Blocks

   CORPUS_DESIGN
   CORPUS
   KNOWLEDGE_BASE
   BACKENDS
   backends/index
   CONTEXT_PACK

Extraction and Ingestion
------------------------

Extraction turns raw files into usable text. Biblicus supports pluggable extractors so you can
mix plain text handling with OCR, document parsers, and speech-to-text pipelines.

.. toctree::
   :maxdepth: 2
   :caption: Extraction and Ingestion

   EXTRACTION
   EXTRACTION_EVALUATION
   extractors/index
   STT

Retrieval and Evaluation
------------------------

Retrieval is how you move from a large corpus to a compact, relevant evidence set. These pages
cover baseline retrieval, hybrid strategies, and how to evaluate retrieval quality.

.. toctree::
   :maxdepth: 2
   :caption: Retrieval and Evaluation

   RETRIEVAL
   RETRIEVAL_QUALITY
   RETRIEVAL_EVALUATION

Analysis and Modeling
---------------------

Analysis tools help you find structure inside large text corpora. Topic modeling provides a
first pass at clustering themes. Markov analysis (Hidden Markov Models) adds sequence modeling
to detect recurring phases in longer documents or conversations.

.. toctree::
   :maxdepth: 2
   :caption: Analysis and Modeling

   PROFILING
   TOPIC_MODELING
   MARKOV_ANALYSIS

Toolbox
-------

Reusable building blocks support common transformations in information pipelines. They are
designed to be simple to invoke while enabling sophisticated behavior under the hood, so you can
slot them into ETL-like workflows without building a custom agent every time.

.. toctree::
   :maxdepth: 2
   :caption: Tools

   UTILITIES
   TEXT_UTILITIES
   TEXT_EXTRACT
   TEXT_SLICE
   TEXT_ANNOTATE
   TEXT_REDACT
   TEXT_LINK

Operations and Demos
--------------------

Operational docs help you run the system, configure it, and reproduce examples. The demo guides
are designed to be runnable end-to-end and serve as acceptance tests.

.. toctree::
   :maxdepth: 2
   :caption: Operations and Demos

   DEMOS
   USER_CONFIGURATION
   TESTING

Reference
---------

Reference material, design notes, and the API index live here. Use this section for deeper
implementation details or when you want a catalog of features.

.. toctree::
   :maxdepth: 1
   :caption: Reference

   FEATURE_INDEX
   ROADMAP
   ARCHITECTURE
   ARCHITECTURE_DETAIL
   PR_FAQ_TEXT_ANNOTATE
   api
