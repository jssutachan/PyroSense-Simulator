# ADR-0005 — Sensors report device health, not fire alerts

**Status:** Accepted (2026-07-07)

## Context

While designing the telemetry payload the question came up: should a node
emit "fire detected" (a flag or an `ALERT` status)?

## Decision

No. `status` ∈ {`OK`, `DEGRADED`, `LOW_BATTERY`} describes **hardware
health**. Fire detection is inferred in the cloud from the raw measurements
(`temp_c`, `smoke_ppm`, `rh_pct`, wind) across the whole fleet.

## Consequences

- Detection logic lives in one place (the cloud), where there is fleet-wide
  context — neighbours, wind, history — and compute; and where it can be
  improved without reflashing thousands of nodes on a mountainside.
- There are no two sources of truth that could contradict each other ("the
  sensor says fire, the model says no").
- The payload carries facts (measurements), not judgments — it ages better.

## Alternatives considered

- **A `fire_alert` flag in the payload**: freezes detection thresholds into
  the contract (and into firmware), creates contradictory alerts and doubles
  the maintenance surface.
- **Hybrid edge+cloud detection**: interesting for latency in the future, but
  requires edge model governance that does not exist today; to be revisited
  with data.
