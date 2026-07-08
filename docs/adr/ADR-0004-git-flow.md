# ADR-0004 — Simplified Git Flow

**Status:** Accepted (2026-07-07)

## Context

The project is built incrementally by a single developer assisted by AI, and
the repository doubles as portfolio evidence: the Git history should tell the
engineering story clearly.

## Decision

Simplified Git Flow, without release/hotfix branches:

- **`main`** — stable/deliverable states only. Never worked on directly.
- **`develop`** — integration branch; every feature starts and ends here.
- **`feature/<descriptive-name>`** — one per feature; branched from
  `develop`, merged back with `--no-ff` once complete and verified.
- **`chore/*`** — cross-cutting work (refactors, documentation), same cycle.
- When a set of features forms a stable milestone: `develop` → `main` with a
  version tag.
- Atomic Conventional Commits; **never** `push --force` or rewriting
  published history.

## Consequences

- `--no-ff` merges keep each feature's cycle visible in the graph — readable
  for a reviewer or interviewer.
- `main` is always demoable.
- Cost: more ceremony than trunk-based development; acceptable without mature
  CI/CD, and valuable as portfolio storytelling.

## Alternatives considered

- **Trunk-based development**: optimal with robust CI and feature flags; too
  many prerequisites at this stage (when to migrate remains an open question).
- **Full Git Flow** (release/hotfix branches): ceremony without formal
  releases yet.
