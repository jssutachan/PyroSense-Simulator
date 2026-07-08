# ADR-0006 — Tooling: uv, src layout, strict mypy, living coverage threshold

**Status:** Accepted (2026-07-07)

## Context

The project requires Python ≥ 3.12; development machines may ship older
interpreters and sudo is not guaranteed. The repository doubles as portfolio
evidence: the tooling should match what a professional team uses today.

## Decision

- **uv** manages the virtual environment and the interpreter itself
  (it downloads CPython 3.12).
- **src layout** (`src/pyrosense_sim/`) with the **hatchling** build backend
  and editable installs.
- **Strict mypy** over `src/` and `tests/`, with the pydantic plugin and
  third-party stubs (`types-shapely`, `types-PyYAML`).
- **ruff** for linting + formatting (E, W, F, I, UP, B, SIM, C4, PT, RUF).
- **pytest-cov** with a threshold that rises with the project, and
  **warnings-as-errors** with documented exceptions.

## Consequences

- Reproducible on any machine without touching the system Python.
- The src layout forces tests to exercise the installed package, not the
  local directory — packaging bugs surface in development, not production.
- Strict mypy turns design mistakes into type errors (e.g., it forced
  explicit geometry narrowing over shapely operations).

## Alternatives considered

- **deadsnakes/pyenv**: require sudo or are slower; couple the setup to
  the OS.
- **Flat layout**: allows accidental imports of uninstalled code.
- **Classic setuptools**: more boilerplate with no benefit here.
