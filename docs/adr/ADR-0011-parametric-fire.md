# ADR-0011 — Fire events are parametric interpolation, not physics

**Status:** Accepted (2026-07-07)

## Context

The simulator needs "fires" to validate the detection pipeline. Real
fire-spread science exists (Rothermel, FARSITE, fuel models,
slope-wind interactions) — complex and hungry for data we don't have
(fuel maps, dead fuel moisture, etc.).

## Decision

`FireEvent` is **parametric interpolation**: a circle whose radius grows
linearly, whose center drifts with a configurable wind vector, and whose
intensity (0..1) ramps in smoothly (smoothstep) after ignition and decays
linearly across a halo beyond the front. Intensity scales signal deltas
(temperature up, humidity down, smoke way up) over the baseline. Nothing more.

## Consequences

- It produces exactly what the pipeline needs: **plausible multi-sensor
  spatial correlation** (neighbours see the signature, distant nodes don't;
  adaptive cadence fires in the affected zone) with six understandable
  parameters.
- The `january_2024_replay` scenario is a calibrated *signature* of the real
  event, not a reconstruction — and says so in its own YAML.
- Explicit limit: this simulator is not a tool for studying fire spread or
  planning firebreaks. If that is ever needed, it will be a new component
  (external model integration?) with its own ADR.

## Alternatives considered

- **A physical model (Rothermel/FARSITE)**: months of work and nonexistent
  data, for a goal (testing the pipeline) that doesn't require it.
- **Synthetic signals without geometry** (per-node ramps): doesn't produce
  the spatial correlation the detection Lambda must distinguish from faults.
