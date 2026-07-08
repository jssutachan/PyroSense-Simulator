# ADR-0002 — Contract first; telemetry payload v1 is frozen

**Status:** Accepted (2026-07-07)

## Context

The consumer of the telemetry payload (a Lambda behind AWS IoT Core) does not
exist yet. The simulator and the cloud platform will be developed in parallel,
by different people and repositories.

## Decision

Define the telemetry contract **before** any business logic, freeze it as v1
(a literal `schema_version`, `extra="forbid"`, frozen model) and materialize
it as a versioned JSON Schema in `docs/payload-schema-v1.json` guarded by an
anti-drift test. Evolution is additive via a new `schema_version`; v1 is never
edited.

## Consequences

- Both sides can be built in parallel against the same verifiable agreement.
- Integration bugs fail fast and on the producer side (unknown fields are
  rejected), instead of silently corrupting the consumer.
- Cost: changing the payload is deliberately expensive — it requires a new
  version. That friction is accepted in exchange for stability.

## Alternatives considered

- **An implicit schema** ("whatever JSON the code emits"): drifts without
  control and breaks the consumer without warning.
- **`extra="ignore"`**: hides integration errors until production.
- **Sharing only the Python model**: couples the consumer to Python; the JSON
  Schema is language-agnostic.
