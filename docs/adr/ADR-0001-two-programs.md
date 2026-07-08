# ADR-0001 — Two separate programs: site-planner and fleet-sim

**Status:** Accepted (2026-07-07)

## Context

The subsystem must (a) decide where to place sensors over real terrain and
(b) generate continuous telemetry from that fleet toward the cloud. It could
be a single program doing both.

## Decision

Two independent programs communicating through an intermediate artifact (the
GeoJSON deployment plan): **site-planner** (offline, runs once) and
**fleet-sim** (long-running).

## Consequences

- Correct life cycles: planning is a one-off, geospatial-heavy computation
  (rasterio/shapely); simulating is a long-running, I/O-heavy process.
  Separated, each loads only its own dependencies and is tested in isolation.
- The GeoJSON plan is inspectable and versionable: it can be reviewed by hand,
  regenerated, or edited between stages.
- The fleet simulator can run against a handcrafted plan (no DEM required) —
  useful for testing.

## Alternatives considered

- **A monolith with subcommands**: couples dependencies (the simulator would
  drag rasterio along) and mixes life cycles.
- **Inline planning inside the simulator**: would repeat an expensive
  computation and prevent inspecting/adjusting the plan between stages.
