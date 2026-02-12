# Agent Instructions for Biblicus

**For project overview and policies, see [AGENTS.md](AGENTS.md).**

This document gives operational instructions for AI agents working on **Biblicus** (knowledge base and retrieval evaluation). Biblicus uses **Beads** for issue and task tracking; using Beads is **mandatory**.

## Development Guidelines

### Code Standards

- **Python**: Follow [AGENTS.md](AGENTS.md) (Pydantic at boundaries, Sphinx-style docstrings, Black + Ruff).
- **Testing**: Behavior specs in `features/*.feature` (Behave); 100% coverage for `src/biblicus/`. See [docs/TESTING.md](docs/TESTING.md).
- **Linting**: Black and Ruff compliance is mandatory (AGENTS.md).
- **Documentation**: Update relevant docs in `docs/` and keep AGENTS.md current.

### Before Committing

1. **Run tests**: `python scripts/test.py` (or `python scripts/run_all_tests.py` for full suite including integration; see [docs/TESTING.md](docs/TESTING.md)).
2. **Lint**: Ruff and Black (per AGENTS.md).
3. **Update specs**: New behavior must have a failing scenario in `features/*.feature` first, then implementation.
4. **Commit**: Beads auto-syncs to `.beads/issues.jsonl`; include the issue ID in the commit message (see below).

### Commit Message Convention

When committing work for an issue, include the issue ID in parentheses at the end:

```bash
git commit -m "Fix extraction validation (Biblicus-4sx)"
git commit -m "Add real-time extraction API (Biblicus-5fp)"
```

This project uses the **Biblicus** issue prefix (e.g. `Biblicus-4sx`). Including the ID lets `bd doctor` detect orphaned issues (commits that did not close the issue).

### Git and Beads

- **Auto-sync**: Beads exports to `.beads/issues.jsonl` after CRUD (with debounce) and imports when the file is newer (e.g. after `git pull`).
- **Merge conflicts** in `.beads/issues.jsonl`: Resolve with `git checkout --theirs .beads/issues.jsonl` then `bd import -i .beads/issues.jsonl`, or merge manually and run `bd import`.
- **Sync branch**: For a shared sync branch, set `sync-branch` in [.beads/config.yaml](.beads/config.yaml) or run `bd config set sync.branch <branch>`.

## Landing the Plane

**When the user says "let's land the plane"**, you MUST complete ALL steps below. The plane is NOT landed until `git push` succeeds. NEVER stop before pushing. NEVER say "ready to push when you are!" — that is a FAILURE.

**MANDATORY WORKFLOW:**

1. **File Beads issues** for any remaining work that needs follow-up.
2. **Run quality gates** (if code changed):
   - Tests: `python scripts/test.py` (or `python scripts/run_all_tests.py` as appropriate).
   - Lint: Ruff and Black per AGENTS.md.
   - File high-priority issues if quality gates are broken.
3. **Update Beads issues** — close finished work, update status.
4. **PUSH TO REMOTE (MANDATORY):**
   ```bash
   git pull --rebase
   # If conflicts in .beads/issues.jsonl: resolve (e.g. git checkout --theirs .beads/issues.jsonl; bd import -i .beads/issues.jsonl)
   bd sync
   git push
   git status   # MUST show "up to date with origin/main" (or current branch)
   ```
5. **Clean up**: `git stash clear`, `git remote prune origin`.
6. **Verify**: All changes committed and pushed.
7. **Hand off**: Suggest a follow-up issue and a prompt for the next session (e.g. "Continue work on Biblicus-5fp: Add real-time extraction pipeline tracking. Next: implement event publisher in extraction.py.").

**CRITICAL:** Work is NOT complete until `git push` succeeds. If push fails, resolve and retry until it succeeds.

## Agent Session Workflow

**Do not use `bd edit`** — it opens an interactive editor. Use `bd update` with flags:

```bash
bd update <id> --description "new description"
bd update <id> --title "new title"
bd update <id> --status in_progress
bd update <id> --notes "notes"
bd close <id> --reason "Completed: ..."
```

**When you finish making issue changes**, run:

```bash
bd sync
```

That flushes pending changes to JSONL, commits, pulls, imports, and pushes. Without it, changes can sit in the debounce window and not be pushed.

**Recommended:** Install Beads git hooks once per clone:

```bash
bd hooks install
```

Hooks keep `.beads/issues.jsonl` and the Beads database in sync on commit, push, merge, and checkout.

## Using Beads in This Repo

- **Create**: `bd create "Title" -p <priority>` (e.g. `-p 1` critical, `-p 2` high).
- **List**: `bd list` (or `bd ready` for a suggested next issue).
- **Show**: `bd show <id>` (e.g. `bd show Biblicus-5fp`).
- **Update**: `bd update <id> --status in_progress` etc.; never `bd edit`.
- **Close**: `bd close <id> --reason "Completed: ..."`.
- **Sync**: `bd sync` at end of session after any issue changes.

Issue IDs use the **Biblicus** prefix (e.g. `Biblicus-5fp`).

## Checking GitHub Issues and PRs

When asked to check GitHub issues or PRs, use the CLI (e.g. `gh`) rather than browser tools:

```bash
gh issue list --limit 30
gh pr list --limit 30
gh issue view <number>
```

Summarize in conversation: urgent items, themes, and what needs attention.

## Important Files

- **[AGENTS.md](AGENTS.md)** — Project memory, vocabulary, policies, design rules.
- **[README.md](README.md)** — User-facing overview and usage.
- **[docs/TESTING.md](docs/TESTING.md)** — How to run tests and coverage.
- **features/** — BDD specifications; all behavior must be specified here first.
