# Contributing to DevMon

DevMon is a gamified terminal experience — real coding activity powers a
creature-collection RPG layered over your normal shell. Contributions are
welcome; this doc covers the basics of getting set up and the conventions
the codebase follows.

## Dev setup

DevMon uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
uv sync
```

To run the CLI against your working tree:

```bash
uv run devmon --help
```

## Running tests

```bash
uv run python -m pytest -q
```

The suite is the source of truth — please keep it green. If you add a new
command, model field, or engine function, add tests alongside it rather
than after the fact.

## Code style

- **Comments only when non-obvious.** Code should read clearly on its own;
  reserve comments for the "why," not a restatement of the "what."
- **No premature abstraction.** Mirror existing patterns (data-driven JSON
  + `*_loader.py`, Typer sub-app per command group) rather than inventing a
  new one for a single use site.
- **Atomic commits.** One logical change per commit, with a message that
  explains why the change was made.
- Match the existing module you're extending — if you're adding a command,
  read a sibling in `src/devmon/commands/` first and follow its shape.

## Save compatibility

Any new field on `GameState` (or its sub-models) must be additive with a
default, and any `schema_version` bump must include a migration so older
`save.json` files keep loading. Don't break existing saves.

## Submitting changes

1. Fork and branch from `main`.
2. Make your change with tests.
3. Run `uv run python -m pytest -q` and confirm it's green.
4. Open a pull request describing what changed and why.
