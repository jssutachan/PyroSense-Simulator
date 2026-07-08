# ADR-0013 — QoS 1 with deduplication in the cloud

**Status:** Accepted (2026-07-07)

## Context

MQTT offers three delivery levels: QoS 0 (at-most-once, may lose messages),
QoS 1 (at-least-once, may duplicate) and QoS 2 (exactly-once, 4-way
handshake). For wildfire-detection telemetry, losing messages is
unacceptable; what about duplicates?

## Decision

**QoS 1** in the `MqttPublisher`, and **deduplication by `device_id` +
`seq` is the cloud's responsibility**, not the producer's. The v1 payload
already carries everything needed (a per-device monotonic `seq`) — this
decision was seeded into the contract from the start.

## Consequences

- No reading is ever lost by transport design (critical for alerting); the
  cost is that the ingestion Lambda must be **idempotent** against repeated
  `device_id`+`seq` pairs.
- AWS IoT Core does not support QoS 2, so exactly-once was never a real
  option — pretending otherwise in the client would lie to the system.
- The simulator *trains* this responsibility: the `duplicates` fault
  produces exactly the duplicates the cloud will have to absorb.
- End-to-end coherence: an at-least-once network plus an idempotent consumer
  is the standard distributed-systems pattern (the same contract as SQS
  standard queues or Kinesis).

## Alternatives considered

- **QoS 0**: silent reading loss on the least reliable network in the system
  (radio on a mountainside); unacceptable for the use case.
- **QoS 2**: not available in IoT Core; and even if it were, the latency and
  per-message state cost buys nothing that idempotency doesn't provide more
  cheaply.
- **Client-side dedupe**: the client cannot deduplicate what the network
  duplicates after it; only the cloud sees the final stream.
