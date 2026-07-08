# ADR-0008 — Gateways as metadata: no radio simulation

**Status:** Accepted (2026-07-07)

## Context

Real nodes would report via LoRa to gateways. Should the planner simulate RF
propagation (line of sight, path loss, Fresnel zones) to place them and
validate coverage?

## Decision

No. Gateways are **pure metadata**: `ceil(n/capacity)` k-means clusters over
node positions, each centroid snapped to the highest ground within 200 m (the
single physical nod: real LoRa gateways favour elevated sites), and every
node assigned to its nearest gateway. Capacity sizes the cluster count;
nearest-neighbour assignment may exceed it slightly, and that is documented.

## Consequences

- The fleet simulator gets what it needs (a `gateway_id` per node for the
  payload) without derailing the project into an RF problem that is not its
  goal.
- The hand-rolled k-means is ~30 lines of seeded numpy — scikit-learn was
  rejected because it would cost more (a heavy dependency, a large API
  surface) than it buys.
- If real RF coverage validation is ever needed, it will be a new component
  with its own ADR, not a mutation of this one.

## Alternatives considered

- **Full RF simulation**: scope creep; requires data (clutter, antennas)
  that does not exist in this project.
- **Manually placed gateways**: valid for real operations, but the planner
  must propose an automatic starting point.
- **scikit-learn for clustering**: a dependency out of proportion to the
  problem.
