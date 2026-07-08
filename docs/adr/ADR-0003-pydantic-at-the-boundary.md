# ADR-0003 — Pydantic only at the boundary; dataclasses inside

**Status:** Accepted (2026-07-07)

## Context

Pydantic provides excellent validation and JSON serialization, but charges a
per-instance CPU and memory cost (validation on every construction, serdes
machinery). The fleet simulator creates many internal objects per simulation
tick.

## Decision

Pydantic is used **only** where data crosses the process boundary and needs
validation/serialization: `TelemetryPayload`, scenario configuration, and
connection settings. Every internal object — geometries, node state,
already-validated configuration — uses `@dataclass` (with `frozen=True` when
it must be immutable/hashable, like `Zone`).

## Consequences

- Validation happens exactly once, at the edge, where it protects against
  external data; inside, invariants are guaranteed by constructors plus
  strict mypy.
- Internal objects are cheap to create (relevant at thousands of ticks) and
  carry no serialization machinery they don't need.
- A clear rule for future work: "does this object leave the process or come
  from outside? → Pydantic. Does it live and die inside? → dataclass."

## Alternatives considered

- **Pydantic everywhere**: uniformity at the price of per-instance cost and a
  blurred notion of where the system's real boundary is.
- **Raw dicts internally**: no types, no invariants; mypy cannot help.
