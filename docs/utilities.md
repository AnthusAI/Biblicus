# Utilities

These are focused, reusable building blocks that help you transform or interpret text and other artifacts inside
pipelines. They are intentionally small and composable: each one does a single job well, with strict input validation
and predictable output.

## Current utility families

- **Text utilities**: agentic, tool-loop workflows that edit a virtual copy of a text and return structured results.
  - See `docs/text-utilities.md` for the shared mechanism and contracts.
  - See `docs/text-extract.md`, `docs/text-slice.md`, `docs/text-annotate.md`,
    `docs/text-redact.md`, and `docs/text-link.md` for per-utility details.

## Design stance

Utilities are built to be:

- **Reusable**: clear contracts, strict validation, deterministic parsing.
- **Compositional**: small units that can be chained in ETL pipelines.
- **Observable**: errors and warnings are explicit and actionable.

Text utilities are the first family and establish the pattern. Additional utility families should follow the same
discipline: minimal surface area, clear responsibilities, and full behavior specifications.
