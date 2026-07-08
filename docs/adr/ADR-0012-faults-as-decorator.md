# ADR-0012 — Faults are injected into the message stream, not the nodes

**Status:** Accepted (2026-07-07)

## Context

The project requires simulating real IoT network pathologies (nodes going
silent, reconnection bursts with old timestamps, QoS 1 duplicates,
reordering). Where should that logic live? The obvious option was adding
fault states to `SensorNode`.

## Decision

`FaultInjector` is a **decorator over the `Publisher` protocol**: it
implements `publish/close`, wraps any transport (or another injector) and
perturbs the message stream. `SensorNode` was not touched — nodes keep
behaving like healthy hardware; it is *the network and the field* that
misbehave. Simulated time is read from each payload's `ts_device`, so the
injector needs no clock of its own.

## Consequences

- **Real composability**: faults over the baseline, over a fire replay, or
  injectors stacked on each other — without a Cartesian product of
  configurations inside the node.
- Domain separation: *measurement* (node) and *transport* (network) fail in
  different ways; the design now reflects that. `battery_decay` is the edge
  case (it belongs to the device) and is implemented by rewriting the
  stream, accepting that small impurity to keep a single seam.
- A `burst_reconnect` backlog preserves the original `ts_device` values by
  construction (payloads already carry their timestamps) — exactly the case
  the cloud must distinguish from a genuine late alert.
- Open/closed principle in practice: the MQTT transport received the fault
  injector without changing a line.

## Alternatives considered

- **Fault states inside `SensorNode`**: mixes domains, bloats the class, and
  every new fault requires touching the core.
- **Post-processing the NDJSON**: useless for the live MQTT transport.
