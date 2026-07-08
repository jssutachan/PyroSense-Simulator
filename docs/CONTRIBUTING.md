# Contributing and development standard

This document codifies the standard for **all work** on the subsystem.
Every change is born compliant — nothing gets "documented later".

## Workflow (Git)

1. Branch from `develop`: `feature/<descriptive-name>` for features,
   `chore/<name>` for cross-cutting work.
2. **Atomic Conventional Commits**: a semantic prefix (`feat:`, `fix:`,
   `refactor:`, `test:`, `docs:`, `build:`, `chore:`, `style:`), an
   imperative subject of at most 50 characters with no trailing period,
   context in the body, and issue/PR references when they exist.
   One commit = one coherent logical change.
3. Once complete and verified: merge into `develop` with `--no-ff` (after
   maintainer sign-off). A stable milestone = `develop` → `main` plus a
   version tag.
4. Forbidden: `push --force`, deleting branches, or rewriting history
   without explicit authorization.

## Code

- **Python ≥ 3.12**, environment managed with `uv`
  (`uv venv --python 3.12 && uv pip install -e ".[dev]"`).
- Complete type hints; `mypy --strict` clean (also applies to `tests/`).
- **Pydantic only at process boundaries**; internal objects use
  `@dataclass` (frozen when they are value objects) — see
  [ADR-0003](adr/ADR-0003-pydantic-at-the-boundary.md).
- Composition and dependency injection over inheritance; interfaces via
  `Protocol`.
- Specific exceptions with actionable messages; validate at the edges, fail
  early.
- Pure computation separated from I/O; `logging` (never `print`) outside CLI
  entry points.
- **All randomness through an injectable RNG with a configurable seed**
  (reproducible determinism).
- No secrets or absolute paths in code; configuration via `.env`
  (git-ignored).

## Tests

- `tests/` mirrors `src/`; test data is **generated synthetically** (never
  external files or network access).
- Coverage ≥ the current threshold in `pyproject.toml` (it rises with the
  project, never falls).
- Warnings in tests are errors; every filter exception is documented with
  its reason.

## Documentation (docs-as-code)

Mandatory **in the same change as the code** (same PR/branch, never "at the
end"):

- **PEP 257, Google-style docstrings** on all new public API (`Args:` /
  `Returns:` / `Raises:` / `Example:` where it helps); a module docstring in
  every new file.
- Update `README.md`, `docs/architecture.md` and `CHANGELOG.md` whenever the
  change affects what they describe.
- **A new ADR** (`docs/adr/ADR-XXXX-*.md`) whenever the change introduces an
  architecture decision; ADRs are never edited, they are superseded.
- If the contract changes (only via a new version): regenerate
  `docs/payload-schema-v1.json` — the anti-drift test demands it.

## Final verification (checklist before proposing a merge)

```bash
ruff check . && ruff format --check .   # style
mypy                                     # types (strict, src + tests)
pytest                                   # tests + coverage threshold
mkdocs build                             # documentation builds
```

All four green, or there is no merge.
