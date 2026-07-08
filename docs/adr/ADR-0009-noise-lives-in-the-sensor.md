# ADR-0009 — The environment is ground truth; noise lives in the sensor

**Status:** Accepted (2026-07-07)

## Context

The fleet engine needs "per-node seeded gaussian noise" on the readings.
There were two places to put it: in the `EnvironmentModel` or in the
`SensorNode`.

## Decision

`EnvironmentModel.conditions_at()` is a **pure, deterministic function** of
(position, elevation, time): it represents the physical ground truth and
contains no RNG. Seeded gaussian noise lives in `SensorNode.sample()`: each
node derives its RNG from `"{scenario_seed}:{device_id}"` (string seeding
hashes through SHA-512, reproducible across processes) and perturbs its own
readings.

## Consequences

- Physical fidelity: in the real system the instrument is what's noisy, not
  the atmosphere. Two neighbouring nodes read the same truth with independent
  errors — exactly what the detection Lambda will see.
- Determinism is trivial to reason about: the only RNGs in the simulation
  live in the nodes, and each per-node stream is independent of scheduling
  order.
- Fire events perturb ground truth in a single place (`conditions_at`),
  without touching the noise.

## Alternatives considered

- **Noise in the environment**: mixes truth with measurement; query order
  would alter the series (a shared RNG) or require an RNG per spatial query.
- **No noise**: artificially clean telemetry; the cloud platform must be
  tested against realistic signals.
