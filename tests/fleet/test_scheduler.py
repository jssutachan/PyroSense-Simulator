"""Tests for the Scheduler: ordering, horizon, pacing and validation."""

from datetime import UTC, datetime

import pytest

from pyrosense_sim.fleet.config import NodeConfig
from pyrosense_sim.fleet.node import SensorNode
from pyrosense_sim.fleet.scheduler import Scheduler

START = datetime(2026, 1, 15, tzinfo=UTC)


def make_node(device_id: str, t_normal_s: float = 300.0) -> SensorNode:
    return SensorNode(
        device_id=device_id,
        gateway_id="GW-01",
        lon=-74.05,
        lat=4.55,
        elevation_m=2800.0,
        tier=1,
        has_wind_sensor=False,
        config=NodeConfig(t_normal_s=t_normal_s),
        start_time=START,
        seed=1,
    )


def no_sleep(_: float) -> None:
    return None


def test_emissions_are_time_ordered_with_device_tiebreak() -> None:
    nodes = [make_node("PYRO-T1-0002"), make_node("PYRO-T1-0001")]
    scheduler = Scheduler(nodes, duration_s=601.0, speed=1e9, sleep_fn=no_sleep)
    events = list(scheduler.run())

    times = [t for t, _ in events]
    assert times == sorted(times)
    # At each shared instant, devices come in id order (determinism).
    assert [node.device_id for _, node in events[:2]] == ["PYRO-T1-0001", "PYRO-T1-0002"]


def test_sample_count_matches_duration_and_cadence() -> None:
    node = make_node("PYRO-T1-0001", t_normal_s=300.0)
    scheduler = Scheduler([node], duration_s=3600.0, speed=1e9, sleep_fn=no_sleep)
    events = list(scheduler.run())
    assert len(events) == 12  # t = 0, 300, ..., 3300; t=3600 is past the horizon


def test_speed_scales_real_time_pacing() -> None:
    sleeps: list[float] = []
    node = make_node("PYRO-T1-0001", t_normal_s=300.0)
    scheduler = Scheduler([node], duration_s=901.0, speed=60.0, sleep_fn=sleeps.append)
    list(scheduler.run())
    # Emissions at t = 0, 300, 600, 900 (900 < 901): gaps of 0, 300, 300, 300
    # simulated seconds at speed 60 -> 0, 5, 5, 5 real seconds.
    assert sleeps == pytest.approx([0.0, 5.0, 5.0, 5.0])


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"duration_s": 0.0}, "must be positive"),
        ({"duration_s": 100.0, "speed": 0.0}, "must be positive"),
    ],
)
def test_rejects_invalid_parameters(kwargs: dict[str, float], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        Scheduler([make_node("PYRO-T1-0001")], sleep_fn=no_sleep, **kwargs)


def test_rejects_empty_fleet() -> None:
    with pytest.raises(ValueError, match="at least one node"):
        Scheduler([], duration_s=100.0, sleep_fn=no_sleep)
