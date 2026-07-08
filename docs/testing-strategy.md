# System testing strategy

Two validation stages: **Stage 1** proves the simulator is a functional
product on its own (no AWS, runs anywhere); **Stage 2** uses the simulator to
validate the real cloud pipeline once it exists. Stage 1 gates every merge to
`main`; Stage 2 gates the cloud backend's acceptance.

## Stage 1 — Local acceptance (no AWS)

Run after the standard checks (`ruff`, `mypy`, `pytest`, `mkdocs build`).
Each step states what to verify and why it matters.

### 1. Plan the site

```bash
site-planner generate --dem data/dem_cerros_orientales.tif \
    --aoi config/reserve.geojson --out out/ --preview
```

**Verify in `out/site-report.md`:** total nodes in the expected range for
the AOI; achieved densities close to targets (T1 ≈ 4, T2 ≈ 10, T3 ≈ 25
ha/node); relocated > 0 if the terrain has steep areas — and **dropped = 0**
unless the terrain is genuinely impossible; the seed is recorded. Check
`preview.png` visually: nodes should follow the tier bands, and gateways
should sit on high ground.

**Determinism gate:** run the command twice into different directories and
`cmp` the two `sensors.geojson` files — they must be byte-identical.

### 2. Baseline: the boring day (false-positive gate)

```bash
fleet-sim run --site out/sensors.geojson --scenario scenarios/baseline.yaml \
    --publisher stdout --speed 10000000 > baseline.ndjson
```

**Verify:** every node emits exactly `duration_hours * 3600 / t_normal_s`
samples (no node ever entered alert cadence); every `status` is `OK`; max
`smoke_ppm` stays far below the alert threshold. A healthy day must produce
**zero** alert-like signals — this is the false-positive gate.

### 3. Fire replay: the detection gate

```bash
fleet-sim run --site out/sensors.geojson \
    --scenario scenarios/january_2024_replay.yaml \
    --publisher stdout --speed 10000000 > fire.ndjson
```

**Verify:** nodes near the epicenter (−74.052, 4.605) show the correlated
signature (smoke ≫ baseline, temp up, humidity down) while distant nodes
stay flat; the per-hour message rate ramps up as nodes switch to the 30 s
alert cadence; a simple rule (e.g., "≥3 devices above 5 ppm within 10
minutes") fires within the simulation. Record the single-node detection
time vs the multi-node confirmation time — the gap is a *finding* about
sensor density, not a bug.

### 4. Faults: the robustness dataset

```bash
fleet-sim run --site out/sensors.geojson --scenario scenarios/faults.yaml \
    --publisher stdout --speed 10000000 > faults.ndjson
```

**Verify the stream contains, measurably:** duplicate `(device_id, seq)`
pairs (QoS 1); `seq` gaps (dropouts); timestamp regressions (reordering plus
the reconnection burst); `LOW_BATTERY`/`DEGRADED` statuses. Note the trap:
bucketing by `ts_device` hides the gateway outage — the backlog fills the
gap with original timestamps. Arrival order is what reveals it.

### 5. Load: the throughput ceiling

```bash
fleet-sim run --site out/sensors.geojson --scenario scenarios/load_test.yaml \
    --publisher stdout --speed 10000000 > /dev/null   # read stderr logs
```

**Verify:** device count = plan nodes × `fleet_multiplier`, all ids unique;
note the local generation ceiling (payloads / wall seconds) and the
sustained rate the cloud must ingest (payloads / simulated seconds).

## Stage 2 — Cloud pipeline validation (when the AWS backend exists)

Prerequisites: IoT Core endpoint + device certificates provisioned; `.env`
filled from `.env.example`; the ingestion path (IoT rule → Lambda → storage)
deployed.

### 2.1 Connectivity smoke (one device, one message)

Subscribe to `pyrosense/dev/telemetry/#` in the AWS IoT MQTT test client,
then run a tiny fleet (a handcrafted 1-node `sensors.geojson`) for a minute:

```bash
fleet-sim run --site one-node.geojson --scenario scenarios/baseline.yaml \
    --publisher mqtt --speed 60
```

**Verify:** messages appear in the test client on the expected topic; the
publisher log shows `sent=N failed=0`; TLS handshake works with the
provisioned certs. This isolates auth/policy problems from scale problems.

### 2.2 Contract conformance in the cloud

Run baseline for a few simulated hours with `--publisher mqtt`. **Verify:**
the Lambda parses every message against `docs/payload-schema-v1.json` with
zero validation errors; records land in storage with `ts_device` intact and
`Z`-suffixed.

### 2.3 Functional detection test

Run `january_2024_replay` against the cloud. **Verify:** the platform raises
its alert for the El Cable area and **does not** alert during a parallel
baseline run. Measure end-to-end latency: `ts_device` of the triggering
message vs alert emission time.

### 2.4 Robustness test

Run `faults.yaml` against the cloud. **Verify:** duplicates are deduplicated
(storage has one row per `device_id`+`seq`); the reconnection burst does
NOT raise a fire alert (old timestamps + healthy readings); `seq` gaps are
surfaced as device-health metrics, not data corruption.

### 2.5 Load test

Run `load_test.yaml` with `--publisher mqtt`. **Watch in CloudWatch:** IoT
Core inbound message count vs simulator `sent` metric (must match);
Lambda concurrent executions, duration p99, throttles (must be zero);
downstream write capacity. Increase `fleet_multiplier` until something
saturates — that number is the platform's measured capacity.

### 2.6 Chaos day (combined)

Copy the `faults:` block into `january_2024_replay.yaml` (fire + degraded
network simultaneously). **Verify:** the alert still fires despite
dropouts and duplicates. This is the closest rehearsal of January 2024
the system gets before real hardware.

## Acceptance summary

| Gate | Scenario | Pass criterion |
|---|---|---|
| No false positives | `baseline` | 0 alerts, all `OK`, normal cadence |
| Detectability | `january_2024_replay` | correlated multi-sensor signature + cadence burst |
| Robustness | `faults` | all five pathologies measurable; payloads still contract-valid |
| Capacity | `load_test` | fleet × N unique devices; ingest rate sustained |
| Reproducibility | any | same seed ⇒ byte-identical output |
