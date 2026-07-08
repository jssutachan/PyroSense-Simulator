# PyroSense Simulator

Simulation subsystem of **PyroSense**, a serverless AWS platform for early
wildfire detection in Bogotá's Cerros Orientales.

This site documents the subsystem for two audiences:

- **Understanding the design** → start with the
  [architecture guide](architecture.md) (a 10-minute read) and the
  [architecture decision records](adr/index.md).
- **Using or extending the code** → the [API reference](reference.md)
  (generated from docstrings) and the [contributing guide](CONTRIBUTING.md).
- **Validating the system** → the [testing strategy](testing-strategy.md):
  local acceptance gates and the cloud-pipeline validation runbook.

The most important piece of the subsystem is the
[v1 data contract](data-contract.md): the frozen agreement between the
simulated sensors and the cloud platform.

## What's inside

| Component | Description | Status |
|---|---|---|
| Data contract v1 | Frozen telemetry payload + exported JSON Schema | ✅ |
| Publishers | stdout / file (NDJSON) and MQTT toward AWS IoT Core (QoS 1) | ✅ |
| Site planner | DEM + priority zones → deterministic sensor deployment plan + CLI | ✅ |
| Fleet simulator | Environment model, noisy nodes, simulated clock, scenarios + CLI | ✅ |
| Fire events | Parametric multi-sensor fire signatures (January 2024 replay) | ✅ |
| Fault injection | Dropouts, reconnection bursts, duplicates, reordering, battery decay | ✅ |
| Load testing | Fleet replication (~25x baseline volume) | ✅ |

**The simulation subsystem is feature-complete.** Live MQTT publishing
against AWS IoT Core activates once the PyroSense cloud backend exists.
