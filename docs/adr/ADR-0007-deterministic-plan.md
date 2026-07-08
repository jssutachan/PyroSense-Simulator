# ADR-0007 — The deployment plan is deterministic by contract

**Status:** Accepted (2026-07-07)

## Context

The site-planner uses randomness (position jitter, k-means initialization).
Left uncontrolled, two runs would produce different plans: impossible to
review in a diff, to reproduce a bug, or to cite in a report.

## Decision

All randomness flows from **a single configurable seed** (`seed` in
`params.yaml`), and serialization is deterministic by construction: no
timestamps, sorted JSON keys, fixed rounding (coordinates to 6 decimals,
≈ 0.11 m). Same inputs + same seed ⇒ **byte-identical** files (a test
compares raw bytes).

## Consequences

- Plans can be versioned and reviewed like code: an empty diff means nothing
  changed.
- Reproducible debugging; `site-report.md` records the seed used.
- The rule is inherited by the fleet simulator: injectable, seeded RNGs,
  codified in the contribution guide.
- Cost: implicit entropy sources (clocks, external dict ordering,
  non-deterministic parallelism) are forbidden in the planning pipeline.

## Alternatives considered

- **Free-running randomness** (default `random`): irreproducible.
- **Freezing the output as a fixture**: pins the bytes but not the property;
  any legitimate change would break the fixture without explaining why.
