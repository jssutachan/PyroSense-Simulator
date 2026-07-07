"""Tests for SensorNode: valid payloads, seq, battery, status, adaptive cadence."""

from datetime import UTC, datetime

from pyrosense_sim.contracts.telemetry import DeviceStatus, TelemetryPayload
from pyrosense_sim.fleet.config import EnvironmentConfig, NodeConfig
from pyrosense_sim.fleet.environment import EnvironmentModel
from pyrosense_sim.fleet.node import SensorNode

START = datetime(2026, 1, 15, tzinfo=UTC)


def make_node(
    *, has_wind: bool = True, config: NodeConfig | None = None, seed: int = 1
) -> SensorNode:
    return SensorNode(
        device_id="PYRO-T1-0001",
        gateway_id="GW-01",
        lon=-74.05,
        lat=4.55,
        elevation_m=2800.0,
        tier=1,
        has_wind_sensor=has_wind,
        config=config or NodeConfig(),
        start_time=START,
        seed=seed,
    )


def make_env(**overrides: float) -> EnvironmentModel:
    return EnvironmentModel(EnvironmentConfig(**overrides))


def test_sample_produces_valid_contract_payload() -> None:
    payload = make_node().sample(make_env(), 600.0)
    assert isinstance(payload, TelemetryPayload)  # construction already validated it
    assert payload.device_id == "PYRO-T1-0001"
    assert payload.ts_device == datetime(2026, 1, 15, 0, 10, tzinfo=UTC)


def test_seq_is_strictly_monotonic() -> None:
    node = make_node()
    env = make_env()
    seqs = [node.sample(env, 300.0 * i).seq for i in range(10)]
    assert seqs == list(range(10))


def test_node_without_wind_sensor_emits_nulls() -> None:
    payload = make_node(has_wind=False).sample(make_env(), 0.0)
    assert payload.wind_speed_ms is None
    assert payload.wind_dir_deg is None


def test_node_with_wind_sensor_emits_values() -> None:
    payload = make_node(has_wind=True).sample(make_env(), 0.0)
    assert payload.wind_speed_ms is not None
    assert payload.wind_dir_deg is not None


def test_battery_drains_and_drives_status() -> None:
    config = NodeConfig(battery_drain_pct_per_day=86_400.0)  # 1% per simulated second
    node = make_node(config=config)
    env = make_env()

    assert node.sample(env, 0.0).status is DeviceStatus.OK  # first sample: no elapsed time
    assert node.sample(env, 85.0).status is DeviceStatus.LOW_BATTERY  # battery = 15
    payload = node.sample(env, 95.0).status  # battery = 5
    assert payload is DeviceStatus.DEGRADED


def test_cadence_switches_to_alert_when_readings_are_elevated() -> None:
    # Any positive reading crosses a 0 C threshold, even at the nightly minimum.
    node = make_node(config=NodeConfig(alert_temp_c=0.0))
    env = make_env(temp_mean_c=14.0)
    assert node.interval_s == 300.0
    node.sample(env, 0.0)
    assert node.interval_s == 30.0


def test_cadence_returns_to_normal_when_readings_calm_down() -> None:
    node = make_node(config=NodeConfig(alert_temp_c=0.0))
    env_hot = make_env(temp_mean_c=14.0)
    env_cool = make_env(temp_mean_c=-5.0, temp_amplitude_c=0.0)  # ~-6 C at node elevation
    node.sample(env_hot, 0.0)
    assert node.interval_s == 30.0
    node.sample(env_cool, 30.0)
    assert node.interval_s == 300.0


def test_same_seed_same_readings() -> None:
    env = make_env()
    first = make_node(seed=9).sample(env, 300.0)
    second = make_node(seed=9).sample(env, 300.0)
    assert first == second


def test_different_seed_different_noise() -> None:
    env = make_env()
    first = make_node(seed=1).sample(env, 300.0)
    second = make_node(seed=2).sample(env, 300.0)
    assert first.temp_c != second.temp_c
