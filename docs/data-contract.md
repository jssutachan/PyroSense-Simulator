# Data contract — Telemetry v1

The telemetry payload is **the frozen agreement** between the sensors
(simulated or real) and the cloud platform. Source model:
`pyrosense_sim.contracts.telemetry.TelemetryPayload`.
Machine-readable schema: [`payload-schema-v1.json`](payload-schema-v1.json)
(regenerate with
`python -m pyrosense_sim.contracts.export_schema > docs/payload-schema-v1.json`;
an anti-drift test guarantees it never goes stale).

## Example

```json
{
  "schema_version": "1.0",
  "device_id": "PYRO-T1-0042",
  "gateway_id": "GW-01",
  "ts_device": "2026-07-07T12:30:00Z",
  "seq": 7,
  "lat": 4.6097,
  "lon": -74.04,
  "elevation_m": 3050.0,
  "temp_c": 18.5,
  "rh_pct": 65.0,
  "smoke_ppm": 0.02,
  "wind_speed_ms": 3.4,
  "wind_dir_deg": 270.0,
  "battery_pct": 88.0,
  "status": "OK"
}
```

## Field by field

| Field | Type | Validation rule | Why it exists |
|---|---|---|---|
| `schema_version` | str | Literal `"1.0"` | Contract evolution happens by version, never by editing v1. A consumer knows exactly what shape to expect. |
| `device_id` | str | `^PYRO-T[123]-\d{4}$` | Node identity; the tier is embedded (T1/T2/T3) so priority filtering needs no joins. |
| `gateway_id` | str | `^GW-\d{2,}$` | Which gateway aggregated/relayed the message; enables diagnosing per-zone outages. |
| `ts_device` | datetime UTC | Timezone-aware required; serializes as ISO 8601 with `Z` | The **device's** timestamp, not the cloud's. Compared against ingestion time it measures end-to-end latency and detects clock drift. |
| `seq` | int ≥ 0 | Per-device monotonic counter | **Loss and duplicate detection**: a gap in `seq` = lost messages; a repeated `seq` = a duplicate (MQTT QoS 1 may re-deliver). Monotonicity is verified by the consumer. |
| `lat` / `lon` | float | −90..90 / −180..180 | Node position (fixed after deployment, but travels in every message so the consumer needs no external registry). |
| `elevation_m` | float | — | Site elevation (from the DEM); relevant for propagation models. |
| `temp_c` | float | −20..80 | Sane physical range for the Bogotá highlands; anything outside is sensor failure, not weather. |
| `rh_pct` | float | 0..100 | Relative humidity. |
| `smoke_ppm` | float | ≥ 0 | Smoke concentration — the primary signal. |
| `wind_speed_ms` | float \| null | ≥ 0 or `null` | `null` = the node has no anemometer (only some tiers carry one). **The key is never omitted**: a stable shape for the parser. |
| `wind_dir_deg` | float \| null | 0..360 or `null` | Same as above. |
| `battery_pct` | float | 0..100 | Energy health; feeds `LOW_BATTERY`. |
| `status` | enum | `OK` \| `DEGRADED` \| `LOW_BATTERY` | **Device health, never a fire signal** — see [ADR-0005](adr/ADR-0005-device-health-not-alerts.md). |

## Cross-cutting rules

- **Unknown fields are rejected** (`extra="forbid"`): the contract is
  armored in both directions; integration bugs fail fast and on the producer
  side.
- **Flat payload** (no nesting): simplifies column mapping in the analytics
  pipeline and the IoT Core SQL rules.
- **Immutable**: once built and validated, a payload is never mutated; any
  "edit" means building a new one.
