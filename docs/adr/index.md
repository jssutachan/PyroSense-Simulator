# Architecture Decision Records (ADRs)

Every relevant decision is recorded in the
**context → decision → consequences → alternatives** format.
An ADR is never edited to change a decision: a new one supersedes it.

| ADR | Decision | Status |
|---|---|---|
| [0001](ADR-0001-two-programs.md) | Two separate programs: site-planner and fleet-sim | Accepted |
| [0002](ADR-0002-contract-first.md) | Contract first; telemetry payload v1 is frozen | Accepted |
| [0003](ADR-0003-pydantic-at-the-boundary.md) | Pydantic only at the boundary; dataclasses inside | Accepted |
| [0004](ADR-0004-git-flow.md) | Simplified Git Flow (main/develop/feature) | Accepted |
| [0005](ADR-0005-device-health-not-alerts.md) | Sensors report device health, not fire alerts | Accepted |
| [0006](ADR-0006-tooling.md) | Tooling: uv, src layout, strict mypy, living coverage threshold | Accepted |
| [0007](ADR-0007-deterministic-plan.md) | The deployment plan is deterministic by contract | Accepted |
| [0008](ADR-0008-gateways-as-metadata.md) | Gateways as metadata: no radio simulation | Accepted |
| [0009](ADR-0009-noise-lives-in-the-sensor.md) | The environment is ground truth; noise lives in the sensor | Accepted |
| [0010](ADR-0010-stdout-data-channel.md) | stdout is the data channel; logs go to stderr | Accepted |
| [0011](ADR-0011-parametric-fire.md) | Fire events are parametric interpolation, not physics | Accepted |
| [0012](ADR-0012-faults-as-decorator.md) | Faults are injected into the message stream, not the nodes | Accepted |
| [0013](ADR-0013-qos1-dedupe-in-the-cloud.md) | QoS 1 with deduplication in the cloud | Accepted |
