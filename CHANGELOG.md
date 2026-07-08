# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions aligned to project milestones.

## [0.7.0] — MQTT publisher, load testing and subsystem completion — 2026-07-07

### Added
- `MqttPublisher`: mutual TLS toward AWS IoT Core, topic
  `{base}/{env}/telemetry/{device_id}` at **QoS 1**, retries with exponential
  backoff + jitter, periodic metrics logging, zero secrets in logs, and
  configuration via env/`.env` only (pydantic-settings). Deduplication by
  `device_id`+`seq` is the cloud's responsibility — ADR-0013. Fully tested
  against a mocked broker.
- `scenarios/load_test.yaml` + `load.fleet_multiplier`: fleet replication
  with derived, contract-valid device ids (~25x baseline volume at 60 s
  cadence).
- `--publisher mqtt` on the CLI (lazy import: offline transports never touch
  AWS code paths); `config/publisher.example.yaml` documenting all three
  transports.
- Final README with the five interview-defensible design decisions.

### Fixed
- `.env.example`: `PYROSENSE_TOPIC_BASE` aligned with the real topic layout.

## [0.6.0] — Fire events and fault injection — 2026-07-07

### Added
- `FireEvent`: parametric fire (circle with radial growth, wind drift,
  smoothstep ramp-in, decay halo) perturbing the baseline in
  `EnvironmentModel.conditions_at` — interpolation, not physics (ADR-0011).
- `FaultInjector`: composable `Publisher` decorator (ADR-0012) —
  `node_dropout`, `burst_reconnect` (backlog replayed with original
  `ts_device` values and consecutive `seq`), QoS 1 `duplicates`,
  `out_of_order`, `battery_decay`; `SensorNode` untouched.
- Scenarios `january_2024_replay.yaml` (the real fire's signature,
  annotated) and `faults.yaml` (all five faults, composable onto any
  scenario).
- `fires:`/`faults:` scenario blocks with strict validation; shared
  `geo.distance_m`.

## [0.5.0] — Baseline fleet engine — 2026-07-07

### Added
- `fleet/config.py`: scenario YAML validated with strict pydantic (a user
  input boundary); `baseline.yaml` and `dry_season.yaml` (El Niño, no fire)
  scenarios.
- `EnvironmentModel`: pure ground truth — sinusoidal diurnal cycle,
  −6.5 °C/km lapse rate, anticorrelated humidity — ADR-0009.
- `SensorNode`: per-node RNG (`seed:device_id`), monotonic `seq`,
  time-proportional battery drain, threshold-driven `status`, adaptive
  cadence 300 s → 30 s.
- `Scheduler`: deterministic heap (device-id tiebreak) with a simulated
  clock and `--speed`; injectable sleep.
- `FleetOrchestrator`: loads the site plan with fail-early property
  validation, composes everything via dependency injection; SIGINT shuts
  down cleanly with a summary (emitted, per-status, simulated vs real time).
- `fleet-sim run` CLI (typer): stdout = NDJSON data, stderr = logs —
  ADR-0010; runs entirely without AWS credentials.

## [0.4.0] — Complete site planner — 2026-07-07

### Added
- `HexGridPlacement` (behind the `PlacementStrategy` protocol): hexagonal
  grid per tier with density-derived spacing (T1 1 node/4 ha, T2 1/10 ha,
  T3 1/25 ha), seeded ±25 m jitter and accounted slope relocation above
  45° — never silent drops. Wind sensors go to the highest sites (1 in 10
  on T1, 1 in 20 on T2/T3).
- `GatewayPlanner`: seeded numpy k-means (`ceil(n/60)` clusters), snap to
  the highest ground within 200 m, nearest-gateway assignment (`GW-##`).
  Pure metadata — ADR-0008.
- `SitePlan`: assembly with injectable strategy and planner; emits
  `sensors.geojson` (stable schema, the fleet simulator's input),
  `gateways.geojson` and `site-report.md`; **byte-deterministic** output by
  seed — ADR-0007.
- `site-planner generate` CLI (typer) with an optional `--preview` PNG (the
  `preview` extra); `config/params.example.yaml`; `PlannerParams` with
  fail-early YAML validation.
- `planner/geo.py`: unified degree↔meter conversion.

### Changed
- `pyproject.toml`: `site-planner` entry point, `preview` extra
  (matplotlib), `types-PyYAML` in dev.

## [0.3.0] — Site planner: terrain and zones — 2026-07-07

### Added
- `TerrainModel`: GeoTIFF loading (rasterio), normalization to EPSG:4326
  with bilinear reprojection, `elevation_at`/`slope_at` queries with
  actionable errors.
- `Zone`/`ZoneSet`: T1/T2/T3 priority polygons, `tier_of` lookup, GeoJSON
  loading and a documented default derivation (western edge + trails).
- Tests with 100% synthetic DEMs (ramp, flat, nodata, UTM).
- Warnings-as-errors policy for tests.

## [0.2.0] — Data contract v1 and publishers — 2026-07-07

### Added
- **Frozen** `TelemetryPayload` v1: pydantic, `extra="forbid"`, frozen,
  `ts_device` in UTC with a `Z` suffix, nullable-but-never-omitted wind
  keys — ADR-0002/0005.
- The contract's JSON Schema in `docs/payload-schema-v1.json` plus an
  anti-drift test.
- The `Publisher` interface (Protocol) and the `stdout` (NDJSON) and `file`
  (NDJSON with size rotation) publishers.
- Coverage threshold raised to 90 (actual: 100%); strict mypy extended to
  tests with the pydantic plugin.

## [0.1.0] — Scaffolding and tooling — 2026-07-07

### Added
- src layout (`src/pyrosense_sim/`), `pyproject.toml` (hatchling),
  dependency groups, and tooling: ruff (lint+format), strict mypy,
  pytest-cov — ADR-0006.
- `.gitignore` (secrets, caches, geospatial binaries), `.env.example`,
  `data/README.md` with the DEM download guide (IGAC / Copernicus GLO-30).
- Packaging smoke test.
